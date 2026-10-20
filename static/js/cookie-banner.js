// Cookie consent + Google Analytics.
// Analytics is only loaded after the visitor clicks "Godta alle" (Google Consent Mode v2, basic mode).
// The choice is stored for a year and can be changed from the "Informasjonskapsler" link in the footer.

const CONSENT_DAYS = 365;

function getConsentCookie(name){
    const match = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : null;
}

function setConsentCookie(name, value){
    const secure = location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = name + '=' + value + '; max-age=' + (CONSENT_DAYS * 24 * 60 * 60) + '; path=/; SameSite=Lax' + secure;
}

function deleteAnalyticsCookies(){
    // Remove Google Analytics cookies (_ga, _ga_XXXX) on this domain and its parent domain
    const host = location.hostname.replace(/^www\./, '');
    document.cookie.split('; ').forEach(function(cookie){
        const name = cookie.split('=')[0];
        if (name === '_ga' || name.indexOf('_ga_') === 0 || name === '_gid'){
            ['', '; domain=' + host, '; domain=.' + host].forEach(function(domain){
                document.cookie = name + '=; max-age=0; path=/' + domain;
            });
        }
    });
}

function loadAnalytics(gaId){
    if (!gaId || window.brakastolenAnalyticsLoaded) return;
    window.brakastolenAnalyticsLoaded = true;

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function(){ window.dataLayer.push(arguments); };
    window.gtag('consent', 'update', { analytics_storage: 'granted' });

    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(gaId);
    document.head.appendChild(script);

    window.gtag('js', new Date());
    window.gtag('config', gaId);
}

function showCookieBanner(banner){
    banner.hidden = false;
    requestAnimationFrame(function(){
        banner.classList.add('active');
    });
}

function hideCookieBanner(banner){
    banner.classList.remove('active');
    setTimeout(function(){
        banner.hidden = true;
    }, 300);
}

document.addEventListener('DOMContentLoaded', function(){
    const banner = document.getElementById('cookieBanner');
    if (!banner) return;

    const gaId = banner.dataset.gaId;
    const cookieName = banner.dataset.cookieName;
    const choice = getConsentCookie(cookieName);

    if (choice === 'all'){
        loadAnalytics(gaId);
    } else if (!choice){
        showCookieBanner(banner);
    }

    banner.querySelectorAll('[data-consent]').forEach(function(button){
        button.addEventListener('click', function(){
            const value = button.dataset.consent;
            setConsentCookie(cookieName, value);
            if (value === 'all'){
                loadAnalytics(gaId);
            } else {
                if (window.gtag){
                    window.gtag('consent', 'update', { analytics_storage: 'denied' });
                }
                deleteAnalyticsCookies();
            }
            hideCookieBanner(banner);
        });
    });

    // "Informasjonskapsler" link in the footer reopens the banner so the choice can be changed
    document.querySelectorAll('[data-cookie-settings]').forEach(function(link){
        link.addEventListener('click', function(e){
            e.preventDefault();
            showCookieBanner(banner);
        });
    });
});
