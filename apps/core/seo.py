"""SEO data shared by every page: business facts (NAP), structured data (JSON-LD), FAQ and partners.

Keep the business facts here only, so name, address and phone are identical
everywhere – search engines and AI assistants compare them across the web.
Facts come from the old website and Brønnøysundregistrene (checked 20.10.2026).
"""
from django.conf import settings
from django.templatetags.static import static

BUSINESS = {
    # The brand visitors know; the legal company behind it is Tranberg Utvikling AS
    'name': 'Brakastølen',
    'tagline': 'Vaset i Valdres',
    'company': 'Tranberg Utvikling AS',
    'legal_name': 'TRANBERG UTVIKLING AS',
    'org_number': '925233498',
    'org_number_display': '925 233 498',
    'description': (
        'Hyttetomter på Brakastølen, Vaset i Valdres – 900 til 1050 meter over havet, '
        'med utsikt mot Jotunheimen og sol fra morgen til kveld. Tomter fra 900 000 kr, '
        'uten byggeklausul, og nøkkelferdige hytter fra utvalgte leverandører.'
    ),
    'phone': '+4748258000',
    'phone_display': '482 58 000',
    'email': 'post@brakastolen.no',
    # Daily manager and chair of the board (brreg.no). Founder is not listed publicly.
    'manager': 'Haakon Bernhard Edland',
    'manager_title': 'Daglig leder',
    # The person buyers talk to (the client's own wording, 22.10.2026)
    'contact_name': 'Haakon B. Edland',
    'contact_title': 'Tomteselger',
    'founding_date': '2020-06-09',
    'founding_year': '2020',
    'employees': None,  # not registered in brreg.no
    # Registered business address (brreg.no) – the company has no office at Vaset
    'street': 'Tranbergvegen 31',
    'postal_code': '2819',
    'city': 'Gjøvik',
    'region': 'Innlandet',
    'country': 'NO',
    # The cabin area itself
    'place_name': 'Brakastølen, Vaset',
    'place_street': 'Brakastølvegen',
    'place_postal_code': '2960',
    'place_city': 'Røn',
    'municipality': 'Vestre Slidre',
    # The middle of the plots: geo.plan_to_latlon of the plots' average position on the site plan,
    # checked against Kartverket's addresses on Brakastøllie and Øyebakkin (27.10.2026).
    'latitude': 61.01754,
    'longitude': 8.94333,
    'maps_url': 'https://www.google.com/maps/search/?api=1&query=61.01754%2C8.94333',
    # Norgeskart (Kartverket) uses UTM zone 33 – the same point, converted with Kartverket's own service
    'norgeskart_url': 'https://norgeskart.no/#!?project=norgeskart&layers=1002&zoom=14&lat=6779884&lon=172925'
                      '&markerLat=6779884&markerLon=172925&p=searchOptionsPanel',
    'area_served': ['Vaset', 'Vestre Slidre', 'Valdres', 'Innlandet'],
    'services': [
        'Hyttetomter', 'Nøkkelferdige hytter', 'Hytteprosjekter', 'Tomteutvikling',
    ],
    'price_from': 900000,
    'price_from_display': '900 000 kr',
    'altitude': '900–1050 moh.',
    'distances': {
        'Fagernes': 'ca. 18 km',
        'Oslo': 'ca. 200 km',
    },
    # No Facebook, Instagram or Google Business profile was found (20.10.2026)
    'same_as': [],
}

# Partners named on the old website ("Våre samarbeidspartnere på Brakastølen")
PARTNERS = [
    ('Hytteleverandør', 'Tinde Hytter', 'https://www.tindehytter.no'),
    ('Hytteleverandør', 'FAUN Gruppen: Leve Hytter, Telemarkhytter, Øverbygg, Nordlyshytter, Familiehytta', 'https://www.levehytter.no'),
    ('Hytteleverandør', 'Slidre Bygg & Prosjektering', 'https://www.slidre-bygg.no'),
    ('Byggmester', 'RH Kvalitetsbygg AS', 'https://www.rhkvalitetsbygg.no'),
    ('Opparbeidelse av tomt og grunnmur', 'VA Entreprenør AS', ''),
    ('Planlegging av hytte på tomt', 'Plan og Oppmåling Valdres AS', ''),
    ('Finansiering', 'SpareBank 1 Hallingdal Valdres', ''),
    ('Oppgjørsmegler', 'EIE Fjellmegleren Fagernes', ''),
    ('Byggesak', 'Vestre Slidre kommune', ''),
]

# The cabin suppliers and builders shown as cards on the homepage («Våre hytteleverandører»).
# Texts written from each company's own website (read 22.10.2026); photos from those sites are
# in static/images/suppliers/. Tinde and Leve get a large card (FEATURED_SUPPLIERS: their section
# on the Hytter page is the last field); the rest a smaller one. (name, what they are, text, link, photo)
FEATURED_SUPPLIERS = [
    ('Tinde Hytter', 'Stedet for dine beste stunder',
     'Serier av kvalitetshytter, alle med hver sine særtrekk – bygget spesielt for deg og dine.',
     'https://www.tindehytter.no', 'images/projects/tinde-vaset-3939.jpg', 'tinde'),
    ('Leve Hytter', 'Tidløst design og solid håndverk',
     'Hytteserien Vy er tegnet sammen med en av Norges fremste arkitekter, i flere grunnmodeller og størrelser.',
     'https://www.levehytter.no', 'images/projects/leve-hytter-vy-overblikk.jpg', 'leve'),
]
SUPPLIERS = [
    ('Telemarkhytter', 'Hytteleverandør i FAUN Gruppen',
     'Nøkkelferdige hytter på ett plan, med hems eller oppstue – tilpasset dine behov, med rådgivere fra første møte.',
     'https://telemarkhytter.no', 'images/suppliers/telemarkhytter.jpg'),
    ('Øverbygg', 'Hytteleverandør i FAUN Gruppen',
     'Skreddersydde tømmerhytter i ekte norsk laft fra Snåsa – over 1400 hytter og boliger levert gjennom mer enn 35 år.',
     'https://overbygg.no', 'images/suppliers/overbygg.jpg'),
    ('Nordlyshytter', 'Hytteleverandør i FAUN Gruppen',
     'Mye lys og luft og store vindusflater. Leveres som byggesett, elektroklare eller nøkkelferdige hytter.',
     'https://nordlyshytter.no', 'images/suppliers/nordlyshytter.jpg'),
    ('Familiehytta', 'Hytteleverandør i FAUN Gruppen',
     'Over 5000 leverte hytter, på ett plan eller med hems – en trygg prosess fra første møte til nøkkel i døra.',
     'https://familiehytta.no', 'images/suppliers/familiehytta.jpg'),
    ('Slidre Bygg & Prosjektering', 'Totalentreprenør i Vestre Slidre',
     'Lokalt forankret totalentreprenør med 18 ansatte og lang erfaring med arkitekttegnede prosjekter.',
     'https://www.slidre-bygg.no', 'images/suppliers/slidrebygg.jpg'),
    ('RH Kvalitetsbygg', 'Byggmester på Lillehammer',
     'Sentralt godkjent byggmester med over 20 års erfaring – spesialister på laft og stavlaft, fra grunnarbeid til nøkkelferdig.',
     'https://www.rhkvalitetsbygg.no', 'images/suppliers/rhkvalitetsbygg.jpg'),
]

FAQ = [
    {
        'question': 'Hva koster en hyttetomt på Brakastølen?',
        'answer': 'Tomtene har pris fra 900 000 kr pluss omkostninger. Ta kontakt for prospekt med pris på de ledige tomtene.',
    },
    {
        'question': 'Er det byggeklausul på tomtene?',
        'answer': 'Nei, det er ingen byggeklausul på tomtene. Vi bistår likevel gjerne med et nøkkelferdig hytteprosjekt hvis du ønsker det.',
    },
    {
        'question': 'Hvor høyt ligger tomtene, og hvordan er solforholdene?',
        'answer': 'Alle tomtene ligger 900–1050 meter over havet, med utsikt i 180 grader mot Jotunheimen og sol fra morgen til kveld.',
    },
    {
        'question': 'Kan dere levere en nøkkelferdig hytte?',
        'answer': (
            'Ja. Sammen med utvalgte samarbeidspartnere som Tinde Hytter og Leve Hytter leverer vi nøkkelferdige '
            'hytteprosjekter. Har du egne tegninger, bruker vi et lokalt byggmesterfirma. Du velger tomt og hyttemodell, '
            'så tar vi oss av hele byggeprosessen til hytta står ferdig.'
        ),
    },
    {
        'question': 'Hvor ligger Brakastølen?',
        'answer': (
            'Brakastølen ligger på Vaset i Vestre Slidre kommune, ved Panoramavegen mellom Valdres og Hemsedal – '
            'ca. 18 km nordvest for Fagernes og ca. 200 km fra Oslo.'
        ),
    },
    {
        'question': 'Hva kan man gjøre på Vaset?',
        'answer': (
            'Vaset skiheiser har 9 nedfarter, og løypenettet for langrenn er på ca. 120 km. '
            'Om sommeren er området et eldorado for sykling og fotturer, med merkede sykkelløyper fra Gomobu.'
        ),
    },
    {
        'question': 'Hvordan avtaler jeg visning?',
        'answer': 'Ring grunneier og utbygger på 482 58 000, send e-post til post@brakastolen.no eller fyll ut kontaktskjemaet, så avtaler vi en personlig visning.',
    },
]


def site_url():
    return settings.SITE_URL.rstrip('/')


def absolute(url):
    """Turn '/static/x.jpg' or '/media/x.jpg' into a full https URL."""
    if not url:
        return ''
    if url.startswith('http'):
        return url
    return site_url() + url


def organization_id():
    return site_url() + '/#organization'


def place_id():
    return site_url() + '/#place'


def business_schema():
    b = BUSINESS
    data = {
        '@type': 'LocalBusiness',
        '@id': organization_id(),
        'name': b['name'],
        'alternateName': b['company'],
        'legalName': b['legal_name'],
        'description': b['description'],
        'url': site_url() + '/',
        'logo': absolute(static('images/logo/logo-brakastolen-hvit.png')),
        'image': absolute(static('images/hero/hero-1-tranberg-utvikling-vaset.jpg')),
        'telephone': b['phone'],
        'email': b['email'],
        'priceRange': f"Fra {b['price_from_display']}",
        'identifier': {
            '@type': 'PropertyValue',
            'propertyID': 'Organisasjonsnummer',
            'value': b['org_number'],
        },
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': b['street'],
            'postalCode': b['postal_code'],
            'addressLocality': b['city'],
            'addressRegion': b['region'],
            'addressCountry': b['country'],
        },
        'geo': {'@type': 'GeoCoordinates', 'latitude': b['latitude'], 'longitude': b['longitude']},
        'hasMap': b['maps_url'],
        'areaServed': [{'@type': 'Place', 'name': place} for place in b['area_served']],
        'knowsAbout': b['services'] + ['Hytte på Vaset', 'Hyttefelt i Valdres'],
        'foundingDate': b['founding_date'],
        'employee': {'@type': 'Person', 'name': b['manager'], 'jobTitle': b['manager_title']},
        'contactPoint': {
            '@type': 'ContactPoint',
            'name': f"{b['contact_name']}, {b['contact_title'].lower()}",
            'telephone': b['phone'],
            'email': b['email'],
            'contactType': 'sales',
            'areaServed': 'NO',
            'availableLanguage': ['Norwegian'],
        },
        'containsPlace': {'@id': place_id()},
    }
    if b['same_as']:
        data['sameAs'] = b['same_as']
    return data


def place_schema():
    """The cabin area itself, so map and AI searches for 'Brakastølen' find the right spot."""
    b = BUSINESS
    return {
        '@type': 'Place',
        '@id': place_id(),
        'name': b['place_name'],
        'description': 'Hyttefelt på Vaset i Valdres, 900–1050 moh., ved Panoramavegen mellom Valdres og Hemsedal.',
        'address': {
            '@type': 'PostalAddress',
            'streetAddress': b['place_street'],
            'postalCode': b['place_postal_code'],
            'addressLocality': b['place_city'],
            'addressRegion': b['region'],
            'addressCountry': b['country'],
        },
        'geo': {'@type': 'GeoCoordinates', 'latitude': b['latitude'], 'longitude': b['longitude']},
        'containedInPlace': {'@type': 'AdministrativeArea', 'name': f"{b['municipality']} kommune"},
    }


def website_schema():
    return {
        '@type': 'WebSite',
        '@id': site_url() + '/#website',
        'url': site_url() + '/',
        'name': f"{BUSINESS['name']} – {BUSINESS['tagline']}",
        'inLanguage': 'nb-NO',
        'publisher': {'@id': organization_id()},
    }


def breadcrumb_schema(items):
    """items: list of (name, path) after the home page, e.g. [('Tomter', '/tomter/')]."""
    crumbs = [('Hjem', '/')] + list(items)
    return {
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i, 'name': name, 'item': absolute(path)}
            for i, (name, path) in enumerate(crumbs, start=1)
        ],
    }


def service_schema(name, description, path, service_type=None):
    return {
        '@type': 'Service',
        '@id': absolute(path) + '#service',
        'name': name,
        'serviceType': service_type or name,
        'description': description,
        'url': absolute(path),
        'provider': {'@id': organization_id()},
        'areaServed': {'@id': place_id()},
    }


def faq_schema(faq=None):
    return {
        '@type': 'FAQPage',
        'mainEntity': [
            {
                '@type': 'Question',
                'name': item['question'],
                'acceptedAnswer': {'@type': 'Answer', 'text': item['answer']},
            }
            for item in (faq or FAQ)
        ],
    }


def graph(*nodes):
    return {'@context': 'https://schema.org', '@graph': [n for n in nodes if n]}
