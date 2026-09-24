"""Traductions des emails de commande (confirmation + pret au retrait)."""

ORDER_T = {
 "fr": {"subject": "Reçu — commande {num} confirmée ✅", "hello": "Bonjour{first},",
        "confirmed": "Votre commande <strong>{num}</strong> est confirmée et payée {pay} — mode de retrait : <strong>{mode}</strong>.",
        "pay_uc": "en UC", "pay_cb": "par carte",
        "mode_drive": "Drive", "mode_delivery": "Livraison", "mode_point": "Relais {point}",
        "slot": "🕐 Créneau de retrait{date} : <strong>{slot}</strong>", "slot_date": " le {d}", "slot_fee": " — frais de créneau : <strong>{fee:g} UC</strong>",
        "promo": "⚡ Remise promo appliquée : vous avez économisé {amt} €",
        "total": "Total payé : <strong>{total}</strong>",
        "notice": "Vous serez prévenu(e) dès que votre commande sera prête à retirer.",
        "r_subject": "Commande {num} prête au retrait", "r_hello": "Bonjour {first},", "r_default_name": "cher coopérateur",
        "r_good_news": "Bonne nouvelle ! Votre commande <strong>#{num}</strong> est <span style='color:#57D19A;font-weight:600;'>prête</span> au point de retrait :",
        "r_point": "Point de retrait", "r_slot": "🕐 Votre créneau : <strong>{slot}</strong>",
        "r_qr": "Présentez-vous avec votre QR-code de commande pour le retrait."},
 "en": {"subject": "Receipt — order {num} confirmed ✅", "hello": "Hello{first},",
        "confirmed": "Your order <strong>{num}</strong> is confirmed and paid {pay} — pickup mode: <strong>{mode}</strong>.",
        "pay_uc": "in UC", "pay_cb": "by card",
        "mode_drive": "Drive", "mode_delivery": "Delivery", "mode_point": "Pickup point {point}",
        "slot": "🕐 Pickup slot{date}: <strong>{slot}</strong>", "slot_date": " on {d}", "slot_fee": " — slot fee: <strong>{fee:g} UC</strong>",
        "promo": "⚡ Promo discount applied: you saved €{amt}",
        "total": "Total paid: <strong>{total}</strong>",
        "notice": "You will be notified as soon as your order is ready for pickup.",
        "r_subject": "Order {num} ready for pickup", "r_hello": "Hello {first},", "r_default_name": "dear cooperator",
        "r_good_news": "Good news! Your order <strong>#{num}</strong> is <span style='color:#57D19A;font-weight:600;'>ready</span> at the pickup point:",
        "r_point": "Pickup point", "r_slot": "🕐 Your slot: <strong>{slot}</strong>",
        "r_qr": "Please bring your order QR code for pickup."},
 "es": {"subject": "Recibo — pedido {num} confirmado ✅", "hello": "Hola{first},",
        "confirmed": "Su pedido <strong>{num}</strong> está confirmado y pagado {pay} — modo de retirada: <strong>{mode}</strong>.",
        "pay_uc": "en UC", "pay_cb": "con tarjeta",
        "mode_drive": "Drive", "mode_delivery": "Entrega", "mode_point": "Punto {point}",
        "slot": "🕐 Franja de retirada{date}: <strong>{slot}</strong>", "slot_date": " el {d}", "slot_fee": " — coste de franja: <strong>{fee:g} UC</strong>",
        "promo": "⚡ Descuento promo aplicado: ha ahorrado {amt} €",
        "total": "Total pagado: <strong>{total}</strong>",
        "notice": "Le avisaremos en cuanto su pedido esté listo para retirar.",
        "r_subject": "Pedido {num} listo para retirar", "r_hello": "Hola {first},", "r_default_name": "estimado cooperador",
        "r_good_news": "¡Buenas noticias! Su pedido <strong>#{num}</strong> está <span style='color:#57D19A;font-weight:600;'>listo</span> en el punto de retirada:",
        "r_point": "Punto de retirada", "r_slot": "🕐 Su franja: <strong>{slot}</strong>",
        "r_qr": "Preséntese con el código QR de su pedido para la retirada."},
 "gcf": {"subject": "Rési — konmann {num} konfirmé ✅", "hello": "Bonjou{first},",
        "confirmed": "Konmann a'w <strong>{num}</strong> konfirmé é péyé {pay} — mòd rétré : <strong>{mode}</strong>.",
        "pay_uc": "an UC", "pay_cb": "èvè kat",
        "mode_drive": "Drive", "mode_delivery": "Livrézon", "mode_point": "Rèlè {point}",
        "slot": "🕐 Krénò rétré{date} : <strong>{slot}</strong>", "slot_date": " jou {d}", "slot_fee": " — frè krénò : <strong>{fee:g} UC</strong>",
        "promo": "⚡ Rabé promo apliké : ou ékonomizé {amt} €",
        "total": "Total péyé : <strong>{total}</strong>",
        "notice": "Nou ké di'w lè konmann a'w paré pou rétré.",
        "r_subject": "Konmann {num} paré pou rétré", "r_hello": "Bonjou {first},", "r_default_name": "chè koopératè",
        "r_good_news": "Bon nouvèl ! Konmann a'w <strong>#{num}</strong> <span style='color:#57D19A;font-weight:600;'>paré</span> o pwen rétré :",
        "r_point": "Pwen rétré", "r_slot": "🕐 Krénò a'w : <strong>{slot}</strong>",
        "r_qr": "Vin èvè QR-kòd a konmann a'w pou rétré'y."},
 "ar": {"subject": "إيصال — تم تأكيد الطلب {num} ✅", "hello": "مرحباً{first}،",
        "confirmed": "تم تأكيد طلبكم <strong>{num}</strong> ودفعه {pay} — طريقة الاستلام: <strong>{mode}</strong>.",
        "pay_uc": "بوحدات UC", "pay_cb": "بالبطاقة",
        "mode_drive": "درايف", "mode_delivery": "توصيل", "mode_point": "نقطة {point}",
        "slot": "🕐 فترة الاستلام{date}: <strong>{slot}</strong>", "slot_date": " يوم {d}", "slot_fee": " — رسوم الفترة: <strong>{fee:g} UC</strong>",
        "promo": "⚡ خصم ترويجي مطبَّق: وفرتم {amt} €",
        "total": "الإجمالي المدفوع: <strong>{total}</strong>",
        "notice": "سيتم إشعاركم فور جاهزية طلبكم للاستلام.",
        "r_subject": "الطلب {num} جاهز للاستلام", "r_hello": "مرحباً {first}،", "r_default_name": "عزيزي المتعاون",
        "r_good_news": "خبر سار! طلبكم <strong>#{num}</strong> <span style='color:#57D19A;font-weight:600;'>جاهز</span> في نقطة الاستلام:",
        "r_point": "نقطة الاستلام", "r_slot": "🕐 فترتكم: <strong>{slot}</strong>",
        "r_qr": "يرجى إبراز رمز QR الخاص بطلبكم عند الاستلام."},
}


def order_lang(user_doc) -> str:
    lang = (user_doc or {}).get("preferred_language") or "fr"
    return lang if lang in ORDER_T else "fr"


def rtl_wrap(lang: str, inner: str) -> str:
    if lang == "ar":
        return f"<div dir='rtl' style='text-align:right'>{inner}</div>"
    return inner
