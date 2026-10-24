/* Typeset only mathematics near the viewport; do not typeset the entire book at once. */
window.MathJax={startup:{typeset:false},svg:{fontCache:'global'},options:{enableMenu:false}};
window.addEventListener('load',()=>{
  if(!window.MathJax?.startup?.promise)return;
  window.MathJax.startup.promise.then(()=>{
    let queue=Promise.resolve();
    const observer=new IntersectionObserver(entries=>{
      for(const entry of entries)if(entry.isIntersecting){
        observer.unobserve(entry.target);
        queue=queue.then(()=>window.MathJax.typesetPromise([entry.target])).catch(()=>{});
      }
    },{rootMargin:'500px'});
    document.querySelectorAll('.math').forEach(element=>observer.observe(element));
  });
});
