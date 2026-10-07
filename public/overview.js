(() => {
  const toolbar = document.querySelector('.toolbar');
  if (!toolbar) return;
  const section = document.createElement('section');
  section.className = 'daily-overview';
  section.hidden = true;
  section.setAttribute('aria-labelledby', 'overview-heading');
  const heading = document.createElement('h2');
  heading.id = 'overview-heading';
  heading.textContent = 'Today in a sentence';
  const paragraph = document.createElement('p');
  section.append(heading, paragraph);
  toolbar.before(section);
  const styles = document.createElement('style');
  styles.textContent = '.daily-overview{border-top:1px solid var(--line);border-left:3px solid var(--accent);padding:20px 24px;margin:0 0 30px;background:#eeeee4}.daily-overview[hidden]{display:none}.daily-overview h2{font:12px monospace;letter-spacing:1px;color:var(--accent);margin:0 0 12px}.daily-overview p{font-size:clamp(17px,1.8vw,22px);line-height:1.55;max-width:1050px;margin:0;letter-spacing:-.02em}@media(max-width:700px){.daily-overview{padding:18px}}';
  document.head.append(styles);
  let requestNumber = 0;
  async function load(path) {
    const current = ++requestNumber;
    section.hidden = true;
    try {
      const url = new URL(path || 'data/latest.json', document.baseURI);
      if (url.origin !== window.location.origin) return;
      const response = await fetch(url, {cache:'no-store'});
      if (!response.ok) return;
      const edition = await response.json();
      if (current !== requestNumber) return;
      const text = edition.today_in_a_sentence;
      if (typeof text === 'string' && text.trim()) {
        paragraph.textContent = text;
        section.hidden = false;
      }
    } catch (_) { section.hidden = true; }
  }
  const selector = document.querySelector('#edition');
  if (selector) selector.addEventListener('change', e => load(e.target.value));
  load(selector && selector.value);
})();
