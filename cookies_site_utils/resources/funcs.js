function createSidebar(theme = 'cookie-box', mainPage = false, lang = 'ja') {
    let indexUrl = mainPage ? 'index.html' : '../index.html';
    let back = `<a class="logo" href="${indexUrl}"></a>`;
    let lightDark0 = '<span id="mode-toggle-0">&#x1f317;</span>';
    let lightDark1 = '<a id="mode-toggle-1">ライト・ダーク切替</a>';
    let gitHub;
    switch (theme) {
        case 'cookipedia':
            gitHub = '<a href="https://github.com/CookieBox26/cookipedia/issues">Issues</a>';
            break;
        default:
            gitHub = '<a href="https://github.com/CookieBox26/cookie-box/issues">Issues</a>';
    }

    let content = '';
    content += `<h2 class="logo">${back}</h2>`;
    if (!mainPage) {
        content += `<p>ご指摘等は ${gitHub} までご連絡ください</p>`;
        document.getElementById('smartphone-header').innerHTML += back + lightDark0;
    } else {
        document.getElementById('smartphone-header').innerHTML += '<span></span>' + lightDark0;
    }

    content += `<p>${lightDark1}</p>`;
    content += '<p><a href="#">ページの一番上に戻る</a></p>';
    let index = '<h5>ページ内の小見出し一覧</h5>';
    const allHeaders = document.querySelectorAll('h2, h3');
    for (var i = 0; i < allHeaders.length; ++i) {
        index += '<p class="';
        if (allHeaders[i].tagName == 'H3') {
            index += 'indent';
        }
        index += '">';
        index += '<a href="#head' + String(i) + '">';
        index += allHeaders[i].textContent + '</a></p>';
        allHeaders[i].innerHTML += '<a id="head' + String(i) + '"></a>';
    }
    content += `<div id="headers">${index}</div>`;
    if (mainPage) {
        let div = document.createElement('div');
        div.innerHTML = content;
        let ref = document.getElementById('header-externallink');
        document.getElementById('sidebar').insertBefore(div, ref);
    } else {
        document.getElementById('sidebar').innerHTML += content;
    }

    document.documentElement.setAttribute('data-mode', 'dark');
    const saved = localStorage.getItem('mode');
    if (saved) document.documentElement.setAttribute('data-mode', saved);
    for (var i = 0; i < 2; ++i) {
        document.getElementById(`mode-toggle-${i}`).addEventListener('click', () => {
            const cur = document.documentElement.getAttribute('data-mode');
            const next = cur === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-mode', next);
            localStorage.setItem('mode', next);
        });
    }
}

function setButton(id, handle) {
    let button = document.getElementById(id);
    button.addEventListener("click", handle);
    button.addEventListener("touchstart", handle);
}

function setButtonOpenClose(id0, id1) {
    let target = document.getElementById(id1);
    target.style.display = "none";
    setButton(id0, () => {
        target.style.display = (target.style.display == "none") ? "block" : "none";
    });
}

function loadMathJax() {
    window.MathJax = {tex: {inlineMath: [['$', '$']]}};
    const script = document.createElement('script');
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/mathjax/4.0.0/tex-chtml.min.js";
    script.defer = true;
    script.crossOrigin = "anonymous";
    script.referrerPolicy = "no-referrer";
    script.integrity = "sha512-cHFHvgPwgoSbpMuTqgZCOWHzoFqt48aXErA98EcvAiZdN6v2bz416BjOqhZJ4tm+QzVkdeLY6NpEWYEjHBx49w==";
    document.head.appendChild(script);
}

function secureExternalLinks(root = document) {
    const originHost = location.host;
    root.querySelectorAll('a[href]').forEach((a) => {
        const href = a.getAttribute('href');
        if (!href) return;
        if (href.startsWith('#') || href.startsWith('mailto:')) return;
        const url = new URL(href, location.href);
        if (url.host === originHost) return;
        a.setAttribute('target', '_blank');
        const rel = (a.getAttribute('rel') || '').split(/\s+/);
        ['noopener', 'noreferrer'].forEach(v => {
            if (!rel.includes(v)) rel.push(v);
        });
        a.setAttribute('rel', rel.filter(Boolean).join(' '));
    });
}

function init(mainPage = false, lang = 'ja') {
    createSidebar(mainPage, lang);
    secureExternalLinks();
}

document.addEventListener('DOMContentLoaded', () => {
    const s = document.getElementById('app');
    init(s?.dataset.theme || 'cookie-box', s?.dataset.mainpage === 'true', s?.dataset.lang || 'ja');
    if (s?.dataset.mathjax === 'true') loadMathJax();
});

(function () {
    if (typeof Prism === 'undefined' || typeof document === 'undefined') return;
    Prism.hooks.add('before-sanity-check', function (env) {
        env.code = env.code.replace(/^(?:\r?\n|\r)/, '');
    });
})();
