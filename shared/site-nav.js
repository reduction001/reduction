(() => {
'use strict';
const lists=[...document.querySelectorAll('[data-site-nav], .navigation')];
if(!lists.length)return;
const styleId='reduction-nav-divider-style';
if(!document.getElementById(styleId)){
  const style=document.createElement('style');
  style.id=styleId;
  style.textContent=`
.navigation .nav-section{
  display:block!important;
  margin:28px 0 0!important;
  padding:22px 0 12px!important;
  border:0!important;
  border-top:1px solid #3a3a3a!important;
  list-style:none;
  color:#aaa9a3!important;
}
.navigation .nav-section-label{
  display:block;
  font-family:monospace;
  font-size:11px;
  font-weight:400;
  line-height:1.6;
  letter-spacing:1.6px;
  color:#aaa9a3;
}
.navigation .nav-section+li{border-top:0!important}
`;
  document.head.append(style);
}
let last='';
function normalize(value){
  const u=new URL(value,location.href);
  u.hash='';u.search='';
  u.pathname=u.pathname.replace(/\/index\.html$/,'/').replace(/\/$/,'')||'/';
  return u.href;
}
function group(items){
  const top=[],sections=new Map();
  for(const item of items){
    const section=String(item.section||'').trim();
    if(!section)top.push(item);
    else{if(!sections.has(section))sections.set(section,[]);sections.get(section).push(item);}
  }
  return {top,sections};
}
function link(item){
  const li=document.createElement('li'),a=document.createElement('a');
  const title=document.createElement('span'),label=document.createElement('span');
  const arrow=document.createElement('span'),note=document.createElement('span');
  a.href=item.url;title.className='nav-title';label.textContent=item.label;
  arrow.textContent='↗';arrow.setAttribute('aria-hidden','true');
  title.append(label,arrow);note.className='nav-note';note.textContent=item.description||'';
  a.append(title,note);
  if(normalize(item.url)===normalize(location.href))a.setAttribute('aria-current','page');
  li.append(a);return li;
}
function divider(name){
  const li=document.createElement('li'),heading=document.createElement('span');
  li.className='nav-section';heading.className='nav-section-label';heading.textContent=name;
  heading.setAttribute('role','heading');heading.setAttribute('aria-level','2');
  li.append(heading);return li;
}
function render(data){
  if(!data||!Array.isArray(data.items))return;
  const valid=data.items.filter(item=>{try{return item.label&&['https:','http:'].includes(new URL(item.url).protocol);}catch{return false;}});
  if(!valid.length)return;
  const signature=JSON.stringify(valid);
  if(signature===last||lists.some(list=>list.contains(document.activeElement)))return;
  last=signature;
  const {top,sections}=group(valid);
  for(const list of lists){
    const fragment=document.createDocumentFragment();
    for(const item of top)fragment.append(link(item));
    for(const [name,items]of sections){fragment.append(divider(name));for(const item of items)fragment.append(link(item));}
    list.replaceChildren(fragment);
  }
}
async function refresh(){
  if(document.hidden)return;
  try{
    const url=document.documentElement.dataset.navManifest||'./site-navigation.json';
    const response=await fetch(url,{cache:'no-cache'});
    if(response.ok)render(await response.json());
  }catch{/* Keep the existing HTML menu if navigation data cannot load. */}
}
if(window.REDUCTION_NAV)render(window.REDUCTION_NAV);else refresh();
setInterval(()=>{if(!window.REDUCTION_NAV)refresh();},60000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!window.REDUCTION_NAV)refresh();});
})();
