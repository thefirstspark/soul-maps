/* Color Codex Wheel — the nine-slice wheel keyed on the Radiant Number.
   DL-014 (2026-09-05): masters 11/22/33 are a tint of their reduced light, not slices.
   Source of truth for the mapping: RADIANT_WHEEL in soul_map_generator.py and
   tierFromRadiant() in soul-pattern-generator.html. Keep all three in sync. */
(function(){
  var TIERS = [
    {slice:1,  radiant:'1',       name:'Ember',        color:'Ember',  role:'The First Heat',   hex:'#ff6a3d', dark:false},
    {slice:2,  radiant:'2',       name:'Dawn',         color:'Red',    role:'The Will',         hex:'#e24b4a', dark:false},
    {slice:3,  radiant:'3',       name:'Gold Vein',    color:'Gold',   role:'The Orchestrator', hex:'#d4af37', dark:true},
    {slice:4,  radiant:'4',       name:'Verdant Gate', color:'Green',  role:'The Field',        hex:'#10b981', dark:false},
    {slice:5,  radiant:'5',       name:'Tide Glass',   color:'Cyan',   role:'The Signal',       hex:'#22d3ee', dark:true},
    {slice:6,  radiant:'6',       name:'Still Water',  color:'Blue',   role:'The Mind',         hex:'#3b82f6', dark:false},
    {slice:7,  radiant:'7',       name:'Violet Hour',  color:'Purple', role:'The Transformer',  hex:'#8b5cf6', dark:false},
    {slice:8,  radiant:'8',       name:'Rose Ash',     color:'Rose',   role:'The Bond',         hex:'#f43f5e', dark:false},
    {slice:9,  radiant:'9',       name:'Pearl Gate',   color:'White',  role:'The All',          hex:'#f0f0ff', dark:true}
  ];
  window.CODEX_WHEEL_TIERS = TIERS;
  /* Masters reduce for colour and wear it Moonsilvered (35% toward white) with the master ring. */
  function tint(h){ var n=parseInt(h.slice(1),16), t=function(c){return Math.round(c+(255-c)*0.35);};
    return '#'+[(n>>16)&255,(n>>8)&255,n&255].map(function(c){return t(c).toString(16).padStart(2,'0');}).join(''); }
  window.codexTint = tint;
  window.CODEX_MASTERS = {
    11: { reducesTo: 2, color: 'Red',   name: 'Dawn',         base: '#e24b4a',   hex: tint('#e24b4a') },
    22: { reducesTo: 4, color: 'Green', name: 'Verdant Gate', base: '#10b981', hex: tint('#10b981') },
    33: { reducesTo: 6, color: 'Blue',  name: 'Still Water',  base: '#3b82f6',  hex: tint('#3b82f6') }
  };

  function slug(t){ return t.color.toLowerCase(); }

  window.renderCodexWheel = function(mount, opts){
    opts = opts || {};
    var CX=400, CY=400, R0=opts.inner||118, R1=opts.outer||300, N=TIERS.length, step=2*Math.PI/N;
    var P=function(r,a){ a-=Math.PI/2; return [CX+r*Math.cos(a), CY+r*Math.sin(a)]; };
    var f=function(n){ return n.toFixed(1); };
    var legend = opts.legend !== false;
    var s='<svg viewBox="0 0 800 '+(legend?880:800)+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Color Codex wheel: nine slices, one per Radiant Number; masters wear their reduced light tinted">';
    s+='<defs><filter id="cw-glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>';
    s+='<circle cx="'+CX+'" cy="'+CY+'" r="'+(R1+6)+'" fill="none" stroke="rgba(139,92,246,.25)" stroke-width="1"/>';
    TIERS.forEach(function(t,i){
      var a0=i*step, a1=(i+1)*step, am=(a0+a1)/2;
      var o0=P(R1,a0), o1=P(R1,a1), i0=P(R0,a0), i1=P(R0,a1);
      var d='M'+f(i0[0])+' '+f(i0[1])+' L'+f(o0[0])+' '+f(o0[1])+' A'+R1+' '+R1+' 0 0 1 '+f(o1[0])+' '+f(o1[1])+' L'+f(i1[0])+' '+f(i1[1])+' A'+R0+' '+R0+' 0 0 0 '+f(i0[0])+' '+f(i0[1])+'Z';
      var href = opts.linkTo==='codex' ? 'color-codex.html#'+slug(t) : slug(t)+'-soul-journey.html';
      var ink = t.dark ? '#0b0b16' : '#ffffff';
      var lbl=P((R0+R1)/2+6,am), num=P(R1+34,am);
      s+='<a href="'+href+'" class="cw-slice"><title>'+t.color+' · Radiant '+t.radiant+' · '+t.name+' · '+t.role+'</title>';
      s+='<path d="'+d+'" fill="'+t.hex+'" stroke="#050818" stroke-width="3"/>';
      s+='<text x="'+f(lbl[0])+'" y="'+f(lbl[1]-7)+'" text-anchor="middle" font-family="Orbitron,sans-serif" font-size="14" font-weight="700" fill="'+ink+'">'+t.color+'</text>';
      s+='<text x="'+f(lbl[0])+'" y="'+f(lbl[1]+11)+'" text-anchor="middle" font-family="Space Mono,monospace" font-size="9.5" fill="'+ink+'" opacity=".8">'+t.name+'</text>';
      s+='</a>';
      s+='<text x="'+f(num[0])+'" y="'+f(num[1]+5)+'" text-anchor="middle" font-family="Space Mono,monospace" font-size="15" fill="#e0e7ff">'+t.radiant+'</text>';
    });
    s+='<circle cx="'+CX+'" cy="'+CY+'" r="'+(R0-10)+'" fill="#0a0819" stroke="rgba(139,92,246,.35)" filter="url(#cw-glow)"/>';
    s+='<text x="'+CX+'" y="'+(CY-10)+'" text-anchor="middle" font-family="Orbitron,sans-serif" font-size="12" letter-spacing="3" fill="#f59e0b">RADIANT</text>';
    s+='<text x="'+CX+'" y="'+(CY+12)+'" text-anchor="middle" font-family="Space Mono,monospace" font-size="10.5" fill="#9ca3af">Life Path + Expression</text>';
    s+='<text x="'+CX+'" y="'+(CY+28)+'" text-anchor="middle" font-family="Space Mono,monospace" font-size="10.5" fill="#9ca3af">reduced · masters tint</text>';
    if(legend){
      /* DL-014: masters are a tint of their reduced light, shown below the wheel, never as slices. */
      var y=772, keys=[11,22,33], gap=230, x0=CX-gap;
      s+='<text x="'+CX+'" y="'+(y-4)+'" text-anchor="middle" font-family="Orbitron,sans-serif" font-size="11" letter-spacing="3" fill="#f59e0b">MASTERS · MOONSILVERED</text>';
      keys.forEach(function(k,i){
        var m=window.CODEX_MASTERS[k], x=x0+i*gap;
        s+='<a href="'+m.color.toLowerCase()+'-soul-journey.html"><title>Radiant '+k+' → '+m.reducesTo+' '+m.name+' · '+m.color+', tinted toward white</title>';
        s+='<circle cx="'+(x-58)+'" cy="'+(y+30)+'" r="14" fill="'+m.hex+'" stroke="'+m.base+'" stroke-width="3"/>';
        s+='<text x="'+(x-36)+'" y="'+(y+26)+'" font-family="Orbitron,sans-serif" font-size="12" font-weight="700" fill="#e0e7ff">'+k+' → '+m.color+'</text>';
        s+='<text x="'+(x-36)+'" y="'+(y+42)+'" font-family="Space Mono,monospace" font-size="9.5" fill="#9ca3af">'+m.name+' · tinted</text>';
        s+='</a>';
      });
      s+='<text x="'+CX+'" y="'+(y+72)+'" text-anchor="middle" font-family="Space Mono,monospace" font-size="10" fill="rgba(224,231,255,.55)">A master is more light, not another colour. Amber is debt and never a slice.</text>';
    }
    s+='</svg>';
    (typeof mount==='string' ? document.querySelector(mount) : mount).innerHTML = s;
  };
})();
