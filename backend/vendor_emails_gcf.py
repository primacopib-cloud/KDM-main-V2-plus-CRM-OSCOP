"""Templates d'emails du cycle de vie membre en créole antillais (gcf) — fusionnés dans vendor_emails.EMAILS."""

EMAILS_GCF = {
    "activation": {
        "subject": "Aktivé èspas a'w — konvansyon siyé ✔",
        "attached": " — kopi jwenn adan mèl-la",
        "btn": "Aktivé èspas an mwen",
        "html": """<h2 style="color:#451F6B;">Byenvini adan Communityplace, {name} !</h2>
<p>Adézyon a'w <strong>{plan}</strong> péyé é konvansyon tripatit a'w siyé
(kòd vérifikasyon : <strong>{code}</strong>{attached}).</p>
<p>Dènyé étap : aktivé èspas a'w é chwazi modpas a'w :</p>
{btn}
<p style="color:#777;font-size:12px;">Apré sa, ou ké pé voyé pwodui a'w, èvè asistan COOP'IA an nou (gratis) ka gidé'w pa a pa.</p>""",
    },
    "dunning": {
        "subject": "⚠ Prélèvman-la pa pasé — réglé adézyon a'w",
        "btn": "Réglé péyman an mwen",
        "html": """<h2 style="color:#451F6B;">Prélèvman rifizé</h2>
<p>Bonjou {name},</p>
<p>Prélèvman chak mwa pou adézyon a'w <strong>{plan}</strong> pa pasé.
Prèstatè péyman an nou ké réséyé ankò otomatikman,
é nou ké voyé on rapèl chak jou jis ou réglé sa.</p>
{btn}
<p style="color:#777;font-size:12px;">Si ou pa réglé sa, aksè a èspas vandè a'w pé sispann.</p>""",
    },
    "warning": {
        "subject": "⚠ Dènyé rapèl — èspas vandè a'w ké sispann talè",
        "btn": "Réglé péyman an mwen",
        "html": """<h2 style="color:#451F6B;">Poko péyé dépi {days} jou</h2>
<p>Bonjou {name},</p>
<p>Prélèvman pou adézyon a'w <strong>{plan}</strong> poko péyé dépi {days} jou.
Si ou pa réglé sa avan {remaining} jou, aksè a èspas vandè a'w ké sispann otomatikman.</p>
{btn}""",
    },
    "suspended": {
        "subject": "🔒 Èspas vandè sispann — poko péyé dépi plis ki 15 jou",
        "btn": "Réglé péyman an mwen",
        "html": """<h2 style="color:#451F6B;">Èspas vandè a'w sispann</h2>
<p>Bonjou {name},</p>
<p>Malgré rapèl an nou, prélèvman pou adézyon a'w <strong>{plan}</strong>
poko péyé dépi plis ki 15 jou. Aksè a èspas vandè a'w sispann.</p>
{btn}
<p style="color:#777;font-size:12px;">Èspas a'w ké réaktivé otomatikman lè nou risivwè péyman-la.</p>""",
    },
    "reactivated": {
        "subject": "✅ Èspas vandè réaktivé — mèsi pou péyman a'w",
        "html": """<h2 style="color:#451F6B;">Èspas vandè a'w réaktivé</h2>
<p>Bonjou {name},</p>
<p>Nou byen risivwè péyman a'w : aksè a èspas vandè
<strong>{plan}</strong> a'w aktif ankò. Mèsi onpil !</p>""",
    },
    "sign_reminder": {
        "subject": "Fini adézyon a'w — siyé konvansyon a'w",
        "btn": "Siyé konvansyon an mwen",
        "html": """<p>Bonjou {name},</p>
<p>Péyman a'w byen anrijistré. I rété yenki pou konplété é siyé konvansyon a'w :</p>
{btn}""",
    },
    "resume": {
        "subject": "Adézyon a'w ka atann vou — rouprann la ou té rété",
        "btn": "Rouprann adézyon an mwen",
        "html": """<p>Bonjou {name},</p>
<p>Adézyon a'w <strong>{plan}</strong> pa fini. Rouprann enskripsyon a'w èvè on sèl klik :</p>
{btn}
<p style="color:#777;font-size:12px;">Péyman sékirizé, konvansyon siyé an liy, aktivasyon la menm.</p>""",
    },
    "resume2": {
        "subject": "Dènyé rapèl — plas a'w adan koopérativ-la ka atann vou",
        "btn": "Fini adézyon an mwen",
        "html": """<p>Bonjou {name},</p>
<p>Ni dé twa jou, ou koumansé adézyon a'w <strong>{plan}</strong> san fini'y.</p>
<p>Pou rapèl, lè ou ka antré adan santral-la ou ka pwofité la menm :</p>
<ul><li>dé <strong>pri mityalizé</strong> négosyé pou tout manm,</li>
<li>dé on <strong>rézo B2B ESS</strong> aktif adan tout téritwa Outre-mer,</li>
<li>dé on <strong>aktivasyon la menm</strong> apré siyati an liy a konvansyon a'w.</li></ul>
{btn}
<p style="color:#777;font-size:12px;">Sé dènyé rapèl an nou — apré sa dosyé a'w ké achivé.</p>""",
    },
}
