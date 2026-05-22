"""Deterministic test seed for KDM + LOLODRIVE.

This file is safe to call multiple times. It fills the minimum data required by
B2B, ESS route, V2 onboarding/catalog, pickup, vendor, POS and LOLODRIVE tests.
"""
from datetime import datetime, timedelta
from auth import get_password_hash

async def seed_test_database(db):
    now = datetime.utcnow()
    # Users
    users = [
        {
            'id': 'admin-test-id', 'email':'admin@kdmarche-oscop.fr',
            'password_hash': get_password_hash('AdminKDM2025!'),
            'company_name':'KDM Admin', 'siret':'00000000000000', 'contact_name':'Admin',
            'phone':'0590000000', 'subscription':'ess-impact-pro', 'credits':10000,
            'is_admin': True, 'role': 'admin', 'created_at': now, 'updated_at': now,
        },
        {
            'id': 'test-b2b-user-id', 'email':'testb2b@example.fr',
            'password_hash': get_password_hash('TestB2B2025!'),
            'company_name':'Test B2B', 'siret':'11111111111111', 'contact_name':'Test B2B',
            'phone':'0590000001', 'subscription':'ess-impact', 'credits':1000,
            'is_admin': False, 'role': 'buyer', 'created_at': now, 'updated_at': now,
        },
    ]
    for u in users:
        await db.users.update_one({'email': u['email']}, {'$set': u}, upsert=True)

    # Zones / pickup locations
    zones = [
        {'id':'zone-gt','code':'GT','name':'Grande-Terre','label':'Grande-Terre','active':True,'created_at':now},
        {'id':'zone-bt','code':'BT','name':'Basse-Terre','label':'Basse-Terre','active':True,'created_at':now},
        {'id':'zone-971','code':'971','name':'Guadeloupe','label':'Guadeloupe','active':True,'created_at':now},
    ]
    for z in zones:
        await db.zones.update_one({'id': z['id']}, {'$set': z}, upsert=True)
        await db.zones_v2.update_one({'id': z['id']}, {'$set': z}, upsert=True)

    pickups = [
        {'id':'pickup-bm','code':'LP-BAIE-MAHAULT','name':'Lolo Point Baie-Mahault','zone_code':'GT','address':'Baie-Mahault','active':True},
        {'id':'pickup-bt','code':'LP-BASSE-TERRE','name':'Lolo Point Basse-Terre','zone_code':'BT','address':'Basse-Terre','active':True},
    ]
    for p in pickups:
        await db.pickup_locations.update_one({'id': p['id']}, {'$set': p}, upsert=True)

    # Catalog data
    categories = [
        {'id':'cat-epicerie','code':'EPICERIE','name':'Épicerie'},
        {'id':'cat-hygiene','code':'HYGIENE','name':'Hygiène'},
    ]
    for c in categories:
        await db.categories.update_one({'id': c['id']}, {'$set': c}, upsert=True)

    products = [
        {'id':'prod-riz','sku':'RIZ-5KG','name':'Riz long grain 5kg','description':'Riz essentiel','category_id':'cat-epicerie','price_ht_cents':490,'price_public_cents':650,'price_pass_cents':490,'catalog_type':'ESSENTIAL','active':True,'is_active':True},
        {'id':'prod-lait','sku':'LAIT-1L','name':'Lait UHT 1L','description':'Lait essentiel','category_id':'cat-epicerie','price_ht_cents':110,'price_public_cents':140,'price_pass_cents':110,'catalog_type':'ESSENTIAL','active':True,'is_active':True},
        {'id':'prod-huile','sku':'HUILE-1L','name':'Huile végétale 1L','description':'Huile essentielle','category_id':'cat-epicerie','price_ht_cents':320,'price_public_cents':450,'price_pass_cents':320,'catalog_type':'ESSENTIAL','active':True,'is_active':True},
        {'id':'prod-tomacouli','sku':'TOMACOULI-500G','name':'Tomacouli Panzani','description':'Catalogue complémentaire','category_id':'cat-epicerie','price_ht_cents':220,'price_public_cents':220,'catalog_type':'NORMAL','active':True,'is_active':True},
    ]
    for p in products:
        await db.products.update_one({'id': p['id']}, {'$set': p}, upsert=True)
        await db.lolodrive_products.update_one({'sku': p['sku']}, {'$set': p}, upsert=True)
        await db.zone_prices.update_one({'product_id': p['id'], 'zone_code':'GT'}, {'$set': {'id':f"zp-{p['id']}-gt", 'product_id':p['id'], 'zone_code':'GT', 'price_ht_cents':p.get('price_ht_cents', p.get('price_public_cents', 0)), 'active':True}}, upsert=True)
        await db.zone_stocks.update_one({'product_id': p['id'], 'zone_code':'GT'}, {'$set': {'id':f"zs-{p['id']}-gt", 'product_id':p['id'], 'zone_code':'GT', 'qty':100, 'available_qty':100, 'active':True}}, upsert=True)

    # Vendors
    vendor = {'id':'vendor-test','email':'vendor@example.fr','siret':'22222222222222','name':'Vendor Test','status':'approved','created_at':now}
    await db.vendors.update_one({'id': vendor['id']}, {'$set': vendor}, upsert=True)
    await db.vendor_products.update_one({'id':'vendor-prod-riz'}, {'$set': {'id':'vendor-prod-riz','vendor_id':'vendor-test','sku':'RIZ-5KG','name':'Riz vendor','price_ht_cents':450,'active':True}}, upsert=True)

    # ESS route policies/rules/capacity samples
    await db.ess_route_priorities.update_one({'id':'prio-default'}, {'$set': {'id':'prio-default','name':'Default priority','active':True,'score':1}}, upsert=True)
    await db.ess_route_rules.update_one({'id':'rule-default'}, {'$set': {'id':'rule-default','name':'Default rule','active':True,'zone_code':'GT'}}, upsert=True)
    await db.ess_route_capacity.update_one({'id':'cap-default'}, {'$set': {'id':'cap-default','zone_code':'GT','max_orders':100,'active':True}}, upsert=True)

    # LOLODRIVE core data
    await db.lolodrive_logistics_config.update_one({'id':'default'}, {'$set': {
        'id':'default','drive_open_time':'08:00','drive_close_time':'21:30','drive_days':'MON,TUE,WED,THU,FRI,SAT,SUN',
        'drive_fee_min_cents':200,'drive_fee_min_uc':20,'drive_fee_max_cents':300,'drive_fee_max_uc':30,
        'delivery_fee_min_cents':500,'delivery_fee_max_cents':1000,'delivery_fee_min_uc':50,'delivery_fee_max_uc':100,
        'allow_uc_for_normal_if_pass_active': True,'updated_at':now
    }}, upsert=True)
    await db.lolodrive_points.update_one({'code':'LP-BAIE-MAHAULT'}, {'$set': {
        'id':'lp-baie-mahault','code':'LP-BAIE-MAHAULT','name':'Lolo Point Baie-Mahault','city':'Baie-Mahault','status':'ACTIVE','payout_cap_cents_monthly':120000,'payout_cap_percent_bps':600,
        'pass_activation_commission_cents':400,'withdrawal_commission_cents':70,'essential_volume_bps':200,'normal_volume_bps':400
    }}, upsert=True)

    await db.lolodrive_passes.update_one({'user_id':'test-b2b-user-id'}, {'$set': {'id':'pass-test-b2b','user_id':'test-b2b-user-id','status':'ACTIVE','starts_at':now,'ends_at':now+timedelta(days=30),'price_cents':6000,'uc_granted':600,'is_auto_renew':False}}, upsert=True)
    await db.lolodrive_wallets.update_one({'user_id':'test-b2b-user-id'}, {'$set': {'id':'wallet-test-b2b','user_id':'test-b2b-user-id','balance_uc':1000,'created_at':now,'updated_at':now}}, upsert=True)

    await db.lolodrive_partners.update_one({'name':'DARTY'}, {'$set': {'id':'partner-darty','name':'DARTY','type':'Électroménager'}}, upsert=True)
    await db.lolodrive_events.update_one({'id':'event-lolo-hour-darty'}, {'$set': {'id':'event-lolo-hour-darty','type':'LOLO_HOUR','title':'LOLO HOUR Inclusive - Mini lave-vaisselle','starts_at':now+timedelta(days=1),'ends_at':now+timedelta(days=1,hours=1),'is_pass_only':True,'partner_id':'partner-darty','stock_limit':100,'per_user_limit':1,'drive_only':True,'is_active':True}}, upsert=True)

    # CRM O'SCOP bridge seed
    await db.crm_contacts.update_one({'id':'crm-contact-test-b2b'}, {'$set': {'id':'crm-contact-test-b2b','external_user_id':'test-b2b-user-id','email':'testb2b@example.fr','nom':'Test','prenom':'B2B','type_acteur':'client_pass','source_contact':'test_seed','statut_relation':'actif','tags':['PASS_VIE_CHERE','KDMARCHE'],'created_at':now,'updated_at':now}}, upsert=True)
    await db.crm_organizations.update_one({'id':'crm-org-lp-baie-mahault'}, {'$set': {'id':'crm-org-lp-baie-mahault','raison_sociale':'Lolo Point Baie-Mahault','enseigne':'Lolo Point Baie-Mahault','type_structure':'lolo_point_cooperatif','ville':'Baie-Mahault','territoire':'Guadeloupe','statut_ecosysteme':'actif','college_cooperatif':'Relais commerciaux coopératifs','external_lolo_point_id':'lp-baie-mahault','tags':['LOLO_POINT','COOPERATEUR'],'created_at':now,'updated_at':now}}, upsert=True)
    await db.crm_organizations.update_one({'id':'crm-org-darty'}, {'$set': {'id':'crm-org-darty','raison_sociale':'DARTY','enseigne':'DARTY','type_structure':'fournisseur_partenaire','territoire':'Guadeloupe','statut_ecosysteme':'prospect','external_partner_id':'partner-darty','tags':['FOURNISSEUR','LOLO_HOUR'],'created_at':now,'updated_at':now}}, upsert=True)
    await db.crm_opportunities.update_one({'id':'crm-opp-lolo-hour-darty'}, {'$set': {'id':'crm-opp-lolo-hour-darty','titre':'Sponsor LOLO HOUR DARTY','type_besoin':'sponsor_lolo_hour','produit_vise':'Mini lave-vaisselle','pipeline_stage':'activation_planifiee','external_event_id':'event-lolo-hour-darty','tags':['LOLO_HOUR','SPONSOR'],'created_at':now,'updated_at':now}}, upsert=True)
    await db.crm_dossiers.update_one({'id':'crm-dossier-lp-baie-mahault'}, {'$set': {'id':'crm-dossier-lp-baie-mahault','type_dossier':'lolo_point_cooperatif','objet_besoin':'Convention Lolo Point Coopératif','statut':'ouvert','etape_actuelle':'convention_a_signer','external_lolo_point_id':'lp-baie-mahault','created_at':now,'updated_at':now}}, upsert=True)

    return True

async def seed_crm_bridge_data(db):
    now = datetime.utcnow()
    await db.crm_contacts.update_one(
        {'id':'crm-contact-test-b2b'},
        {'$set': {'id':'crm-contact-test-b2b','external_user_id':'test-b2b-user-id','email':'testb2b@example.fr','nom':'Test','prenom':'B2B','type_acteur':'client_pass','source_contact':'test_seed','statut_relation':'actif','tags':['PASS_VIE_CHERE','KDMARCHE'],'created_at':now,'updated_at':now}},
        upsert=True
    )
    await db.crm_organizations.update_one(
        {'id':'crm-org-lp-baie-mahault'},
        {'$set': {'id':'crm-org-lp-baie-mahault','raison_sociale':'Lolo Point Baie-Mahault','enseigne':'Lolo Point Baie-Mahault','type_structure':'lolo_point_cooperatif','ville':'Baie-Mahault','territoire':'Guadeloupe','statut_ecosysteme':'actif','college_cooperatif':'Relais commerciaux coopératifs','external_lolo_point_id':'lp-baie-mahault','tags':['LOLO_POINT','COOPERATEUR'],'created_at':now,'updated_at':now}},
        upsert=True
    )
    await db.crm_organizations.update_one(
        {'id':'crm-org-darty'},
        {'$set': {'id':'crm-org-darty','raison_sociale':'DARTY','enseigne':'DARTY','type_structure':'fournisseur_partenaire','territoire':'Guadeloupe','statut_ecosysteme':'prospect','external_partner_id':'partner-darty','tags':['FOURNISSEUR','LOLO_HOUR'],'created_at':now,'updated_at':now}},
        upsert=True
    )
    await db.crm_opportunities.update_one(
        {'id':'crm-opp-lolo-hour-darty'},
        {'$set': {'id':'crm-opp-lolo-hour-darty','titre':'Sponsor LOLO HOUR DARTY','type_besoin':'sponsor_lolo_hour','produit_vise':'Mini lave-vaisselle','pipeline_stage':'activation_planifiee','external_event_id':'event-lolo-hour-darty','tags':['LOLO_HOUR','SPONSOR'],'created_at':now,'updated_at':now}},
        upsert=True
    )
    await db.crm_dossiers.update_one(
        {'id':'crm-dossier-lp-baie-mahault'},
        {'$set': {'id':'crm-dossier-lp-baie-mahault','type_dossier':'lolo_point_cooperatif','objet_besoin':'Convention Lolo Point Coopératif','statut':'ouvert','etape_actuelle':'convention_a_signer','external_lolo_point_id':'lp-baie-mahault','created_at':now,'updated_at':now}},
        upsert=True
    )
    return True
