(function(){
  'use strict';
  const d = document;
  const oku = (ad, varsayilan) => { try { return JSON.parse(localStorage.getItem(ad)) ?? varsayilan; } catch(e){ return varsayilan; } };
  const yaz = (ad, deger) => { try { localStorage.setItem(ad, JSON.stringify(deger)); } catch(e){} };
  const kacis = s => String(s??'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  let YILDIZ = oku('tr-yildiz', {});
  let BILDIRIM = oku('tr-bildirim', null);

  const bugun = () => { const t=new Date(); return t.getFullYear()+'-'+String(t.getMonth()+1).padStart(2,'0')+'-'+String(t.getDate()).padStart(2,'0'); };
  const turnuvalar = () => (typeof T !== 'undefined' && Array.isArray(T)) ? T : [];
  const bul = id => turnuvalar().find(t => t.id === id);
  const gelecek = t => t && t.end >= bugun();

  function ilListesi(){
    const s = new Set();
    turnuvalar().forEach(t => { if(t.c === 'TR' && t.il && t.il !== 'Türkiye geneli') s.add(t.il); });
    return [...s].sort((a,b)=>a.localeCompare(b,'tr'));
  }
  function bildirimPaneli(){
    const b = BILDIRIM || {secim:null, iller:[], yurtdisi:false};
    const iller = ilListesi();
    if(b.secim){
      const ozet = b.secim==='hic' ? 'Kapalı' : (b.iller.length ? b.iller.join(', ') : 'il seçilmedi') + (b.yurtdisi ? ' + yurt dışı' : '');
      return '<div class="ek-bildirim ek-kapali"><span class="ek-ikon">&#128276;</span><span><b>Bildirimler:</b> ' + kacis(ozet) + '</span><button class="btn sm" data-ek="bildirim-ac">Değiştir</button></div>';
    }
    return '<div class="ek-bildirim">' +
      '<div class="ek-bildirim-bas"><span class="ek-ikon">&#128276;</span><b>Hangi şehirlerdeki turnuvalar sana bildirilsin?</b></div>' +
      '<p class="ek-not">Seçtiğin yerlerde yeni turnuva ilan edilince siteyi açtığında üstte görürsün. İstemiyorsan “Hiçbiri” diyebilirsin; dilediğin zaman değiştirirsin.</p>' +
      '<div class="ek-iller">' + iller.map(i => '<label class="ek-il"><input type="checkbox" value="' + kacis(i) + '" ' + (b.iller.includes(i)?'checked':'') + '> ' + kacis(i) + '</label>').join('') + '</div>' +
      '<label class="ek-il ek-yd"><input type="checkbox" id="ek-yurtdisi" ' + (b.yurtdisi?'checked':'') + '> Yurt dışı turnuvaları da bildir</label>' +
      '<div class="links"><button class="btn pri" data-ek="bildirim-kaydet">Seçtiklerimi kaydet</button><button class="btn" data-ek="bildirim-hic">Hiçbiri, bildirim istemiyorum</button></div></div>';
  }
  function bildirimKaydet(hic){
    const iller = [...d.querySelectorAll('.ek-iller input:checked')].map(x=>x.value);
    const yd = !!(d.getElementById('ek-yurtdisi') && d.getElementById('ek-yurtdisi').checked);
    BILDIRIM = hic ? {secim:'hic', iller:[], yurtdisi:false, sonBakilan:bugun()} : {secim:'sehir', iller:iller, yurtdisi:yd, sonBakilan:bugun()};
    yaz('tr-bildirim', BILDIRIM);
    if(typeof render === 'function') render();
  }
  function bildirimSeridi(){
    if(!BILDIRIM || BILDIRIM.secim !== 'sehir') return '';
    const son = BILDIRIM.sonBakilan || bugun();
    const yeni = turnuvalar().filter(t => gelecek(t) && t.ilk_gorulme && t.ilk_gorulme > son && ((t.c==='TR' && BILDIRIM.iller.includes(t.il)) || (t.c!=='TR' && BILDIRIM.yurtdisi)));
    if(!yeni.length) return '';
    const ozet = yeni.slice(0,4).map(t => kacis((t.il||t.ulke||'') + ' — ' + t.name)).join(' · ');
    return '<div class="ek-uyari"><div><b>Takip ettiğin yerlerde ' + yeni.length + ' yeni turnuva:</b> ' + ozet + (yeni.length>4 ? ' ve ' + (yeni.length-4) + ' tane daha' : '') + '</div>' +
      '<div class="links"><button class="btn pri sm" data-ek="yeni-goster">Göster</button><button class="btn sm" data-ek="uyari-kapat">Okudum</button></div></div>';
  }

  function yildizDugmeleri(t){
    const durum = YILDIZ[t.id];
    return '<button class="btn sm ek-yildiz ' + (durum==='ilgi'?'ek-aktif':'') + '" data-ek="yildiz" data-id="' + kacis(t.id) + '">' + (durum==='ilgi'?'★':'☆') + ' İlgimi çekti</button>' +
      '<button class="btn sm ek-git ' + (durum==='gidiyorum'?'ek-aktif':'') + '" data-ek="gidiyorum" data-id="' + kacis(t.id) + '">' + (durum==='gidiyorum'?'✓':'+') + ' Gidiyorum</button>' +
      '<button class="btn sm" data-ek="paylas" data-id="' + kacis(t.id) + '">Bağlantıyı kopyala</button>';
  }
  function yildizla(id, tur){
    if(YILDIZ[id] === tur) delete YILDIZ[id]; else YILDIZ[id] = tur;
    yaz('tr-yildiz', YILDIZ);
    if(typeof render === 'function') render();
  }

  function paylasBaglantisi(id){
    const u = location.origin + location.pathname + '#t=' + id;
    if(navigator.clipboard) navigator.clipboard.writeText(u).then(()=>uyarVer('Bağlantı kopyalandı')).catch(()=>uyarVer(u));
    else uyarVer(u);
  }
  function uyarVer(mesaj){
    let el = d.getElementById('ek-bildirimcik');
    if(!el){ el = d.createElement('div'); el.id = 'ek-bildirimcik'; el.className = 'ek-toast'; d.body.appendChild(el); }
    el.textContent = mesaj; el.classList.add('ek-gorunur');
    clearTimeout(el._z); el._z = setTimeout(()=>el.classList.remove('ek-gorunur'), 2500);
  }
  function hashTurnuva(){
    const m = /^#t=(.+)$/.exec(location.hash || '');
    return m ? bul(decodeURIComponent(m[1])) : null;
  }

  function benimTurnuvalarim(){
    const hepsi = turnuvalar();
    const gidiyorum = hepsi.filter(t => YILDIZ[t.id]==='gidiyorum' && gelecek(t)).sort((a,b)=>a.start.localeCompare(b.start));
    const ilgi = hepsi.filter(t => YILDIZ[t.id]==='ilgi' && gelecek(t)).sort((a,b)=>a.start.localeCompare(b.start));
    const gecmis = hepsi.filter(t => YILDIZ[t.id] && !gelecek(t)).sort((a,b)=>b.end.localeCompare(a.end));
    const blok = (b, l) => l.length ? '<h2 class="sect">' + b + ' <span>' + l.length + '</span></h2><div class="tlist">' + l.map(t=>tCard(t,true)).join('') + '</div>' : '';
    const bos = !gidiyorum.length && !ilgi.length && !gecmis.length;
    return '<div class="page-h"><h1>Benim turnuvalarım</h1><p>Turnuva kartlarındaki ★ ve ✓ düğmeleriyle işaretlediklerin burada toplanır. Her şey bu tarayıcıda saklanır.</p></div>' +
      (bos ? '<div class="emptybox">Henüz işaretlediğin turnuva yok. Beğendiğin bir turnuvanın altındaki “İlgimi çekti” ya da “Gidiyorum” düğmesine bas.</div>' : '') +
      blok('Gidiyorum', gidiyorum) + blok('İlgimi çekenler', ilgi) + blok('Geçmişte işaretlediklerim', gecmis);
  }
  function paylasilanGorunum(t){
    return '<div class="page-h"><h1>Paylaşılan turnuva</h1><p>Bu bağlantı tek bir turnuvayı gösteriyor.</p></div><div class="tlist">' + tCard(t, true) + '</div>' +
      '<div class="links" style="margin-top:14px"><button class="btn" data-ek="hepsi">Tüm turnuvalara dön</button></div>';
  }

  function sar(){
    if(typeof tCard === 'function' && !tCard._ek){
      const asil = tCard;
      window.tCard = function(t, withCountry){
        let h = asil(t, withCountry);
        if(t && t.id){
          h = h.replace('<article class="tcard">', '<article class="tcard" data-tid="' + kacis(t.id) + '">');
          h = h.replace('<div class="links">', '<div class="links">' + yildizDugmeleri(t));
        }
        return h;
      };
      window.tCard._ek = true;
    }
    if(typeof render === 'function' && !render._ek){
      const asil = render;
      window.render = function(){ asil.apply(this, arguments); sonrasi(); };
      window.render._ek = true;
    }
  }

  function sekmeEkle(){
    const tabs = d.querySelector('.tabs');
    if(!tabs || d.querySelector('[data-view="benim"]')) return;
    const b = d.createElement('button');
    b.className = 'tab'; b.dataset.view = 'benim'; b.textContent = 'Benim turnuvalarım';
    const once = tabs.querySelector('[data-view="calendar"]');
    tabs.insertBefore(b, once ? once.nextSibling : null);
    b.onclick = () => { if(typeof state==='object'){ state.view='benim'; } render(); window.scrollTo({top:0}); };
  }

  function sonrasi(){
    sekmeEkle();
    const app = d.getElementById('app');
    if(!app) return;
    if(typeof state === 'object' && state.view === 'benim') app.innerHTML = benimTurnuvalarim();
    const paylasilan = hashTurnuva();
    if(paylasilan && typeof state === 'object' && state.view === 'home' && !window._ekHash){
      window._ekHash = true;
      app.innerHTML = paylasilanGorunum(paylasilan);
    }
    if(typeof state === 'object' && state.view === 'home'){
      const hero = app.querySelector('.hero');
      if(hero && !app.querySelector('.ek-bildirim')) hero.insertAdjacentHTML('afterend', bildirimPaneli());
    }
    if(!app.querySelector('.ek-uyari')){
      const serit = bildirimSeridi();
      if(serit && app.firstElementChild) app.firstElementChild.insertAdjacentHTML('afterend', serit);
    }
    bagla();
  }

  function bagla(){
    d.querySelectorAll('[data-ek]').forEach(el => {
      if(el._ekBagli) return; el._ekBagli = true;
      const tur = el.dataset.ek;
      el.addEventListener('click', ev => {
        ev.preventDefault(); ev.stopPropagation();
        if(tur === 'yildiz') yildizla(el.dataset.id, 'ilgi');
        else if(tur === 'gidiyorum') yildizla(el.dataset.id, 'gidiyorum');
        else if(tur === 'paylas') paylasBaglantisi(el.dataset.id);
        else if(tur === 'bildirim-kaydet') bildirimKaydet(false);
        else if(tur === 'bildirim-hic') bildirimKaydet(true);
        else if(tur === 'bildirim-ac'){ BILDIRIM = Object.assign({}, BILDIRIM, {secim:null}); yaz('tr-bildirim', BILDIRIM); render(); }
        else if(tur === 'uyari-kapat'){ BILDIRIM.sonBakilan = bugun(); yaz('tr-bildirim', BILDIRIM); render(); }
        else if(tur === 'yeni-goster'){ if(typeof state==='object'){ state.view='yeni'; } BILDIRIM.sonBakilan = bugun(); yaz('tr-bildirim', BILDIRIM); render(); }
        else if(tur === 'hepsi'){ location.hash=''; window._ekHash=false; if(typeof state==='object'){ state.view='home'; } render(); }
      });
    });
  }

  const stil = '.ek-bildirim{background:var(--card);border:1px solid var(--line);border-radius:var(--r-md);padding:14px 16px;margin:18px auto 0;max-width:720px}' +
    '.ek-bildirim.ek-kapali{display:flex;align-items:center;gap:10px;flex-wrap:wrap;font-size:14px;color:var(--muted)}' +
    '.ek-bildirim.ek-kapali b{color:var(--text)}.ek-bildirim.ek-kapali .btn{margin-left:auto}' +
    '.ek-bildirim-bas{display:flex;align-items:center;gap:8px;font-family:"Bricolage Grotesque",sans-serif;font-size:17px}' +
    '.ek-not{color:var(--muted);font-size:13px;margin:6px 0 10px}' +
    '.ek-iller{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:4px;max-height:190px;overflow:auto;padding:8px;background:var(--bg2);border-radius:var(--r-sm)}' +
    '.ek-il{display:flex;align-items:center;gap:7px;font-size:13px;cursor:pointer}.ek-yd{margin-top:10px;font-weight:600}' +
    '.ek-uyari{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between;background:var(--acc-soft);border:1px solid var(--acc);border-radius:var(--r-md);padding:12px 16px;margin-top:16px;font-size:14px}' +
    '.ek-uyari .links{margin:0}.ek-yildiz.ek-aktif,.ek-git.ek-aktif{background:var(--acc);color:var(--acc-ink);border-color:var(--acc)}' +
    '.ek-toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(20px);background:var(--card);color:var(--text);border:1px solid var(--acc);border-radius:999px;padding:10px 18px;font-size:14px;opacity:0;pointer-events:none;transition:opacity .2s,transform .2s;z-index:90}' +
    '.ek-toast.ek-gorunur{opacity:1;transform:translateX(-50%) translateY(0)}.ek-ikon{font-size:17px}';

  function basla(){
    const s = d.createElement('style'); s.textContent = stil; d.head.appendChild(s);
    sar();
    if(typeof render === 'function') render();
    window.addEventListener('hashchange', () => { window._ekHash = false; if(typeof state==='object'){ state.view='home'; } render(); });
  }
  if(d.readyState === 'loading') d.addEventListener('DOMContentLoaded', basla); else basla();
})();
