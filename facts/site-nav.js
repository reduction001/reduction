(() => {
'use strict';
const lists=[...document.querySelectorAll('[data-site-nav], .navigation')];if(!lists.length)return;
let last='';
function normalize(value){const u=new URL(value,location.href);u.hash='';u.search='';u.pathname=u.pathname.replace(/\/index\.html$/,'/').replace(/\/$/,'')||'/';return u.href;}
function render(data){if(!data||!Array.isArray(data.items))return;const valid=data.items.filter(i=>{try{return i.label&&['https:','http:'].includes(new URL(i.url).protocol);}catch{return false;}});if(!valid.length)return;const signature=JSON.stringify(valid);if(signature===last)return;
if(lists.some(list=>list.contains(document.activeElement)))return;last=signature;
for(const list of lists){const fragment=document.createDocumentFragment();for(const item of valid){const li=document.createElement('li'),a=document.createElement('a'),title=document.createElement('span'),label=document.createElement('span'),arrow=document.createElement('span'),note=document.createElement('span');a.href=item.url;title.className='nav-title';label.textContent=item.label;arrow.textContent='↗';arrow.setAttribute('aria-hidden','true');title.append(label,arrow);note.className='nav-note';note.textContent=item.description||'';a.append(title,note);if(normalize(item.url)===normalize(location.href))a.setAttribute('aria-current','page');li.append(a);fragment.append(li);}list.replaceChildren(fragment);}}
async function refresh(){if(document.hidden)return;try{const url=document.documentElement.dataset.navManifest||'./site-navigation.json';const r=await fetch(url,{cache:'no-cache'});if(!r.ok)return;render(await r.json());}catch{/* Keep the accessible HTML fallback. */}}
if(window.REDUCTION_NAV)render(window.REDUCTION_NAV);else refresh();
setInterval(()=>{if(!window.REDUCTION_NAV)refresh();},60000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!window.REDUCTION_NAV)refresh();});
})();
