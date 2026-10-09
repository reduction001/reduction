document.querySelectorAll('.video-play').forEach(b=>{const img=b.querySelector('img');img.addEventListener('error',()=>{img.hidden=true;b.querySelector('span').textContent='▶ Play official video'});b.addEventListener('click',()=>{const id=b.dataset.video;if(!/^[A-Za-z0-9_-]{11}$/.test(id))return;const f=document.createElement('iframe');f.src='https://www.youtube-nocookie.com/embed/'+id+'?autoplay=1';f.title=b.getAttribute('aria-label');f.allow='autoplay; encrypted-media; picture-in-picture';f.allowFullscreen=true;f.style='width:100%;aspect-ratio:16/9;border:0';b.replaceWith(f)})});const all=document.querySelector('#show-videos');if(all)all.addEventListener('click',()=>{const open=all.getAttribute('aria-expanded')!=='true';document.querySelectorAll('[data-extra-video]').forEach(v=>v.hidden=!open);all.setAttribute('aria-expanded',String(open));all.textContent=open?'Show fewer videos':'View all videos'});

(function addParentHistory(){
  const quote=document.querySelector('#parent-market #parent-quote');
  if(!quote||document.querySelector('#parent-history'))return;
  const figure=document.createElement('figure');
  figure.id='parent-history';
  figure.style='margin:22px 0 0;width:100%;max-width:720px;box-sizing:border-box';
  const caption=document.createElement('figcaption');
  caption.className='label';
  caption.textContent='Coca-Cola / NYSE: KO — last 6 months';
  caption.style='margin-bottom:12px';
  const frame=document.createElement('iframe');
  frame.id='parent-history-chart';
  frame.title='Coca-Cola NYSE: KO stock-price history over the last six months';
  frame.src='/dashboards/widgets/ko-history.html';
  frame.style='display:block;width:100%;height:340px;border:1px solid rgba(255,255,255,.12);border-radius:12px;background:#10171c;box-sizing:border-box';
  figure.append(caption,frame);
  quote.insertAdjacentElement('afterend',figure);
})();
