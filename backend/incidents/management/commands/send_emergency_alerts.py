import json
import os
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from incidents.models import EmergencyAlertDelivery

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
EXPO_RECEIPTS_URL = "https://exp.host/--/api/v2/push/getReceipts"
MAX_ATTEMPTS = 3
RETRY_DELAYS = (timedelta(minutes=1), timedelta(minutes=5))


class PushProviderError(Exception):
    def __init__(self, message, code=""):
        super().__init__(message)
        self.code = code


def _request_headers():
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    access_token = os.getenv("EXPO_ACCESS_TOKEN")
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return headers


def _post_json(url, payload):
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=_request_headers(),
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        raise PushProviderError(
            f"El servicio push respondió HTTP {error.code}."
        ) from error
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise PushProviderError("No se pudo contactar el servicio push.") from error

    if not isinstance(response_data, dict):
        raise PushProviderError("El servicio push devolvió una respuesta inválida.")
    return response_data


def send_push_messages(messages):
    response_data = _post_json(EXPO_PUSH_URL, messages)
    tickets = response_data.get("data")
    if not isinstance(tickets, list) or len(tickets) != len(messages):
        raise PushProviderError("El servicio push devolvió una respuesta inválida.")
    return tickets


def parse_push_ticket(ticket):
    if not isinstance(ticket, dict):
        raise PushProviderError("El servicio push devolvió un comprobante inválido.")
    if ticket.get("status") != "ok":
        details = ticket.get("details") or {}
        code = str(details.get("error") or "") if isinstance(details, dict) else ""
        raise PushProviderError(
            f"El servicio push rechazó la solicitud ({code or 'sin código'}).",
            code=code,
        )
    ticket_id = ticket.get("id")
    if not isinstance(ticket_id, str) or not ticket_id:
        raise PushProviderError("El servicio push no devolvió un identificador de comprobante.")
    return ticket_id


def send_push_receipts(ticket_ids):
    response_data = _post_json(EXPO_RECEIPTS_URL, {"ids": ticket_ids})
    receipts = response_data.get("data")
    if not isinstance(receipts, dict):
        raise PushProviderError("El servicio push devolvió comprobantes inválidos.")
    return receipts


def delivery_message(delivery):
    alert = delivery.alert
    if delivery.kind == EmergencyAlertDelivery.Kind.CANCELLATION:
        title = "Alerta de emergencia cancelada"
        body = f"Se canceló la alerta: {alert.title}"
    else:
        title = alert.title
        body = alert.message

    return {
        "to": delivery.device.expo_push_token,
        "sound": "default",
        "title": title,
        "body": body,
        "data": {"alertId": alert.pk, "kind": delivery.kind},
        "priority": "high",
        "ttl": 900,
        "channelId": "emergency-alerts",
        "collapseId": f"nefijj-{delivery.pk}",
    }


def chunks(values, size):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def record_delivery_failure(delivery, error, now):
    delivery.last_error = str(error)[:255]
    if error.code == "DeviceNotRegistered":
        delivery.device.is_active = False
        delivery.device.save(update_fields=["is_active", "updated_at"])
    if error.code == "DeviceNotRegistered" or delivery.attempts >= MAX_ATTEMPTS:
        delivery.status = EmergencyAlertDelivery.Status.FAILED
        delivery.completed_at = now
    else:
        delivery.next_attempt_at = now + RETRY_DELAYS[delivery.attempts - 1]


class Command(BaseCommand):
    help = "Envía notificaciones de emergencia pendientes mediante Expo Push."

    def handle(self, *args, **options):
        pending_ids = list(
            EmergencyAlertDelivery.objects.filter(
                status=EmergencyAlertDelivery.Status.PENDING,
                next_attempt_at__lte=timezone.now(),
            )
            .order_by("created_at", "id")
            .values_list("id", flat=True)[:1000]
        )
        accepted = 0
        failed = 0
        retried = 0

        for batch_ids in chunks(pending_ids, 100):
            with transaction.atomic():
                deliveries = list(
                    EmergencyAlertDelivery.objects.select_for_update()
                    .select_related("alert", "device")
                    .filter(pk__in=batch_ids)
                    .order_by("created_at", "id")
                )
                active_deliveries = []
                for delivery in deliveries:
                    if delivery.status != EmergencyAlertDelivery.Status.PENDING:
                        continue
                    if not delivery.device.is_active:
                        delivery.status = EmergencyAlertDelivery.Status.FAILED
                        delivery.last_error = "El dispositivo está desactivado."
                        delivery.completed_at = timezone.now()
                        delivery.save(
                            update_fields=["status", "last_error", "completed_at"]
                        )
                        failed += 1
                        continue
                    delivery.attempts += 1
                    delivery.save(update_fields=["attempts"])
                    active_deliveries.append(delivery)

                if not active_deliveries:
                    continue

                now = timezone.now()
                try:
                    tickets = send_push_messages(
                        [delivery_message(delivery) for delivery in active_deliveries]
                    )
                except PushProviderError as error:
                    tickets = [error] * len(active_deliveries)

                for delivery, ticket in zip(active_deliveries, tickets):
                    try:
                        if isinstance(ticket, PushProviderError):
                            raise ticket
                        ticket_id = parse_push_ticket(ticket)
                    except PushProviderError as error:
                        record_delivery_failure(delivery, error, now)
                        if delivery.status == EmergencyAlertDelivery.Status.FAILED:
                            failed += 1
                        else:
                            retried += 1
                        delivery.save(
                            update_fields=[
                                "status",
                                "next_attempt_at",
                                "last_error",
                                "completed_at",
                            ]
                        )
                    else:
                        delivery.status = EmergencyAlertDelivery.Status.ACCEPTED
                        delivery.last_error = ""
                        delivery.completed_at = now
                        delivery.provider_ticket_id = ticket_id
                        delivery.receipt_due_at = now + timedelta(minutes=15)
                        delivery.save(
                            update_fields=[
                                "status",
                                "last_error",
                                "completed_at",
                                "provider_ticket_id",
                                "receipt_due_at",
                            ]
                        )
                        accepted += 1

        receipt_failures = self.check_receipts()
        self.stdout.write(
            self.style.SUCCESS(
                f"Expo aceptó {accepted}; fallidas {failed}; "
                f"reintentos programados {retried}; recibos fallidos {receipt_failures}."
            )
        )

    def check_receipts(self):
        due_deliveries = list(
            EmergencyAlertDelivery.objects.filter(
                status=EmergencyAlertDelivery.Status.ACCEPTED,
                provider_ticket_id__gt="",
                receipt_checked_at__isnull=True,
                receipt_due_at__lte=timezone.now(),
            )
            .order_by("receipt_due_at", "id")
            .values_list("id", "provider_ticket_id")[:1000]
        )
        if not due_deliveries:
            return 0

        try:
            receipts = send_push_receipts(
                [ticket_id for _, ticket_id in due_deliveries]
            )
        except PushProviderError as error:
            self.stderr.write(self.style.WARNING(str(error)))
            return 0

        receipt_failures = 0
        for delivery_id, ticket_id in due_deliveries:
            receipt = receipts.get(ticket_id)
            if not isinstance(receipt, dict):
                continue
            with transaction.atomic():
                delivery = (
                    EmergencyAlertDelivery.objects.select_for_update()
                    .select_related("device")
                    .get(pk=delivery_id)
                )
                if delivery.receipt_checked_at is not None:
                    continue
                delivery.receipt_checked_at = timezone.now()
                if receipt.get("status") == "error":
                    details = receipt.get("details") or {}
                    receipt_code = (
                        str(details.get("error") or "")
                        if isinstance(details, dict)
                        else ""
                    )
                    delivery.status = EmergencyAlertDelivery.Status.FAILED
                    delivery.last_error = (
                        f"Expo informó un fallo ({receipt_code or 'sin código'})."
                    )
                    receipt_failures += 1
                    if (
                        isinstance(details, dict)
                        and details.get("error") == "DeviceNotRegistered"
                    ):
                        delivery.device.is_active = False
                        delivery.device.save(update_fields=["is_active", "updated_at"])
                    delivery.save(
                        update_fields=[
                            "status",
                            "last_error",
                            "receipt_checked_at",
                        ]
                    )
                elif receipt.get("status") == "ok":
                    delivery.save(update_fields=["receipt_checked_at"])
        return receipt_failures
