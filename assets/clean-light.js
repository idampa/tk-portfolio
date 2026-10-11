/* Responsive shell; reads the existing portfolio state and reuses its actions. */
(() => {
 const $=s=>document.querySelector(s);
 const make=(tag,cls,html='')=>{const n=document.createElement(tag);n.className=cls;n.innerHTML=html;return n};
 const escape=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const titles={home:['오늘의 포트폴리오','자산의 흐름을 확인하고, 원칙에 따라 기록하세요.'],port:['포트폴리오','계좌별 자산과 보유종목을 한눈에 살펴보세요.'],strategy:['투자 전략','투자 근거부터 매매 조건까지, 판단의 기준을 정리하세요.'],review:['매매 복기','수익과 함께 투자 습관의 변화를 돌아보세요.'],insight:['리서치','관심 종목과 기업 공부를 이어가는 공간입니다.'],more:['설정 및 데이터','시세 관리와 기록 내보내기를 설정하세요.']};
 for(const [key,[title,sub]] of Object.entries(titles)){
  const page=$('#page-'+key);if(!page)continue;
  page.prepend(make('div','page-heading',`<h1>${title}</h1><p>${sub}</p>`));
 }
 const names={home:'오늘',port:'포트폴리오',strategy:'전략',review:'매매 복기',insight:'리서치',more:'설정'};
 document.querySelectorAll('.nav-btn').forEach(b=>{for(const n of [...b.childNodes])if(n.nodeType===3)n.remove();b.append(document.createTextNode(names[b.dataset.page]));b.setAttribute('aria-label',names[b.dataset.page]);});
 const settings=make('button','hdr-btn','설정');settings.onclick=()=>showPage('more',$('.nav-btn[data-page=more]'));$('.hdr-right').append(settings);
 $('.logo').textContent='TK PORTFOLIO';
 const theme=make('button','action-btn primary','다크 모드로 전환');
 const applyTheme=dark=>{document.documentElement.dataset.theme=dark?'dark':'light';theme.textContent=dark?'라이트 모드로 전환':'다크 모드로 전환';theme.setAttribute('aria-pressed',String(dark));};
 try{applyTheme(localStorage.getItem('tk-theme')==='dark')}catch{}
 theme.onclick=()=>{const dark=document.documentElement.dataset.theme!=='dark';applyTheme(dark);try{localStorage.setItem('tk-theme',dark?'dark':'light')}catch{}};
 $('#page-more .page-heading').after(theme);
 const home=$('#page-home');
 const grid=make('div','cl-grid'),primary=make('div','cl-primary'),aside=make('div','cl-aside');grid.append(primary,aside);
 const strip=$('.home-strip'),actions=$('.trade-action-row');
 const summary=make('section','');summary.append(strip,actions);home.insertBefore(summary,home.children[1]);
 actions.children[0].textContent='＋ 매수 기록';actions.children[1].textContent='＋ 매도 기록';actions.children[2].textContent='예수금 관리';
 const chart=make('section','cl-panel cl-trend-panel','<h2>자산 추이</h2><div id="cl-trend" class="cl-chart"></div><div id="cl-trend-dates" class="cl-chart-labels"></div><p class="cl-subtle" id="cl-history-note"></p>');
 const holdings=make('section','cl-panel cl-holdings-panel','<h2>보유종목 <span class="cl-subtle" id="cl-count"></span></h2><div class="cl-holdings"><div class="cl-table-scroll" id="cl-holdings-table"></div><div class="cl-detail" id="cl-detail"></div></div>');primary.append(chart,holdings);
 const holdingsMore=make('button','cl-more cl-holdings-more','보유종목 전체 보기');holdingsMore.onclick=()=>{const expanded=holdings.classList.toggle('expanded');holdingsMore.textContent=expanded?'간단히 보기':'보유종목 전체 보기';holdingsMore.setAttribute('aria-expanded',String(expanded));};holdings.append(holdingsMore);
 const signals=$('#signal-cards'),signalHeading=signals.previousElementSibling;signalHeading.querySelector('.sec-title').textContent='확인할 신호';
 const signalsPanel=make('section','cl-panel cl-signals-panel');signalsPanel.append(signalHeading,signals);aside.append(signalsPanel);
 const signalMore=make('button','cl-more','신호 전체 보기');signalMore.onclick=()=>{const expanded=signalsPanel.classList.toggle('expanded');signalMore.textContent=expanded?'간단히 보기':'신호 전체 보기';signalMore.setAttribute('aria-expanded',String(expanded));};signalsPanel.append(signalMore);
 const events=$('#event-section');events.classList.add('cl-panel');events.querySelector('.event-collapse-title').textContent='투자 일정 기록';events.prepend(make('p','cl-subtle','기존 일정 · 과거 기록이 포함되어 있습니다.'));aside.append(events);
 const principle=$('#insight-card'),principleHeading=principle.previousElementSibling,principlePanel=make('section','cl-panel');principlePanel.append(principleHeading,principle);aside.append(principlePanel);home.append(grid);
 // Group existing portfolio sections without duplicating IDs or calculation paths.
 const port=$('#page-port'),portGrid=make('div','port-grid');let section=null;
 for(const n of [...port.children]){
  if(n.classList.contains('port-section-head')){section=make('section','port-block');portGrid.append(section);}
  if(section)section.append(n);
 }
 port.append(portGrid);
 const note=make('p','cl-note','기존에 작성한 전략·전망 기록입니다. 작성 시점과 현재 보유수량을 확인한 뒤 참고하세요.');$('#page-insight .page-heading').after(note);
 const search=make('input','cl-search');search.type='search';search.placeholder='리서치 내용 검색';search.setAttribute('aria-label','리서치 내용 검색');note.after(search);
 const noResults=make('p','cl-subtle','검색 결과가 없습니다.');noResults.hidden=true;search.after(noResults);
 search.addEventListener('input',()=>{
  const q=search.value.trim().toLocaleLowerCase();let count=0;
  for(const panel of document.querySelectorAll('#insight-panel-watch,#insight-panel-study')){
   let heading=null;
   for(const n of panel.children){if(n.classList.contains('ins-section-head')){heading=n;continue;} const matches=!q||n.textContent.toLocaleLowerCase().includes(q);n.hidden=!matches;if(heading){heading.hidden=!matches;heading=null;}if(matches)count++;}
  }noResults.hidden=count>0;
 });
 let selected=null;
 function holdingsData(){return Object.entries(HOLDINGS).flatMap(([account,rows])=>rows.map(h=>({...h,account})));}
 function selectHolding(key){
  selected=key;const h=holdingsData().find(h=>h.account+':'+h.id===key);if(!h)return;
  const price=Number(PRICES[h.id])||0;const panel=$('#cl-detail');
  panel.innerHTML=`<div><span class="cl-subtle">${h.account==='kiwoom'?'키움':'토스'} · 보유 현황</span><h3>${escape(h.name)}</h3></div><dl><div><dt>보유수량</dt><dd>${fmt(h.qty)}주</dd></div><div><dt>평균 매입가</dt><dd>${fmt(h.avg)}원</dd></div><div><dt>현재가</dt><dd>${fmt(price)}원</dd></div></dl><p>투자 근거와 매매 조건은 작성 시점의 기록입니다. 현재 보유 현황과 함께 확인하세요.</p><button type="button">종목 상세 보기 →</button>`;
  panel.querySelector('button').onclick=()=>openStockDetail(h.id);
  $('#cl-holdings-table').querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.key===key)));
 }
 window.renderCleanDashboard=()=>{
  const rows=holdingsData();$('#cl-count').textContent=rows.length+'종목';
  const s=calcPortStats();
  $('#cl-holdings-table').innerHTML=`<table class="cl-table"><thead><tr><th scope="col">종목</th><th scope="col">평가금액</th><th scope="col">수익률</th><th scope="col" class="cl-extra">비중</th></tr></thead><tbody>${rows.map(h=>{
   const value=(Number(PRICES[h.id])||0)*h.qty,rate=h.avg>0?((PRICES[h.id]-h.avg)/h.avg*100):0;
   return `<tr><td><button data-key="${escape(h.account+':'+h.id)}">${escape(h.name)}<br><span class="cl-subtle">${h.account==='kiwoom'?'키움':'토스'} · ${escape(h.id)}</span></button></td><td>${fmt(value)}원</td><td class="${rate>=0?'up':'dn'}">${rate>=0?'+':''}${rate.toFixed(1)}%</td><td class="cl-extra">${s.grand>0?(value/s.grand*100).toFixed(1):'0'}%</td></tr>`;
  }).join('')}</tbody></table>`;
  $('#cl-holdings-table').querySelectorAll('button').forEach(b=>b.onclick=()=>selectHolding(b.dataset.key));
  if(rows.length)selectHolding(rows.some(h=>h.account+':'+h.id===selected)?selected:rows[0].account+':'+rows[0].id);else $('#cl-detail').textContent='보유종목이 없습니다.';
  const hist=HISTORY.filter(h=>Number.isFinite(Number(h.total)));
  $('#cl-history-note').textContent=(window.tkHistoryLoaded?'저장된 자산 기록 기준':'기존 내장 자산 기록 · 서버 기록 확인 전')+' · 단위: 만원';
  signalMore.hidden=signals.children.length<=3;holdingsMore.hidden=rows.length<=4;
  if(hist.length<2){$('#cl-trend').textContent='자산 기록이 2건 이상 쌓이면 추이가 표시됩니다.';$('#cl-trend-dates').textContent='';return;}
  const vals=hist.map(h=>Number(h.total)),min=Math.min(...vals),max=Math.max(...vals),range=max-min||1;
  const points=vals.map((v,i)=>[58+i/(vals.length-1)*620,175-(v-min)/range*145]);
  const line=points.map(p=>p.join(',')).join(' ');
  $('#cl-trend').innerHTML=`<svg viewBox="0 0 700 210" role="img" aria-label="저장된 자산 ${hist.length}건의 추이, 시작 ${escape(vals[0])}만원, 최근 ${escape(vals.at(-1))}만원" preserveAspectRatio="none">${[0,1,2].map(i=>`<line x1="58" x2="680" y1="${30+i*72.5}" y2="${30+i*72.5}" stroke="var(--border)"/><text x="0" y="${35+i*72.5}" fill="var(--text3)" font-size="11">${Math.round(max-i*range/2).toLocaleString()}</text>`).join('')}<polygon points="58,190 ${line} 678,190" fill="var(--accent)" opacity=".07"/><polyline points="${line}" fill="none" stroke="var(--accent)" stroke-width="3" vector-effect="non-scaling-stroke"/></svg>`;
  $('#cl-trend-dates').innerHTML=`<span>${escape(hist[0].date)}</span><span>${escape(hist.at(-1).date)}</span>`;
 };
 // Refresh presentation even when data has completed loading before this script.
 renderCleanDashboard();
 document.querySelectorAll('.page .sec-title').forEach(n=>{const labels={"STOCK SCORE BOARD":"종목별 투자 점검","UPCOMING EVENTS":"다가오는 일정","CATALYST CALENDAR":"주요 일정"};if(labels[n.textContent.trim()])n.textContent=labels[n.textContent.trim()];});
 document.querySelectorAll('.page [onclick]').forEach(n=>{if(['DIV','SPAN'].includes(n.tagName)&&!n.querySelector('button,input,select,a,[onclick]')){n.tabIndex=0;n.setAttribute('role','button');n.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();n.click();}});}});
 // Desktop review: pair the two overview panels, then a full-width trade journal.
 const review=$('#page-review');
 const overview=make('div','review-overview');
 const habit=$('.rv-score-wrap');
 const performance=make('section','review-performance');
 const cum=$('#cumulative-chart').closest('.card');
 performance.append(cum.previousElementSibling,cum);
 overview.append(habit,performance);review.querySelector('.page-heading').after(overview);
 const journal=make('section','review-journal');
 for(const node of [...review.children])if(node!==overview&&!node.classList.contains('page-heading'))journal.append(node);
 review.append(journal);
 habit.prepend(make('h2','review-panel-title','투자 습관 점검'));
 habit.append(make('p','cl-subtle','점수와 패턴을 확인한 뒤, 아래 거래 기록에서 판단을 돌아보세요.'));
 const watch=$('#insight-panel-watch'),study=$('#insight-panel-study');
 for(const panel of [watch,study]){
  if(!panel)continue;
  const entries=[];let entry=null;
  for(const n of [...panel.children]){
   if(n.classList.contains('ins-section-head')||!entry){entry=make('section','research-entry');entries.push(entry);}
   entry.append(n);
  }
  const browser=make('div','research-browser'),list=make('nav','research-list'),detail=make('div','research-detail');
  list.setAttribute('aria-label','리서치 주제');
  entries.forEach((entry,i)=>{detail.append(entry);const title=entry.querySelector('.ins-section-title')?.textContent||entry.querySelector('.stock-name')?.textContent||'리서치 '+(i+1);const btn=make('button','research-choice',escape(title));btn.type='button';btn.onclick=()=>{entries.forEach((e,j)=>{e.classList.toggle('selected',i===j);list.children[j].setAttribute('aria-pressed',String(i===j));});};list.append(btn);if(i===0){entry.classList.add('selected');btn.setAttribute('aria-pressed','true');}});
  browser.append(list,detail);panel.append(browser);
 }
 // Replace the previous flat search with filtering the topic browser.
 const newSearch=search.cloneNode();search.replaceWith(newSearch);
 newSearch.addEventListener('input',()=>{let total=0;const q=newSearch.value.trim().toLowerCase();
  for(const panel of [watch,study]){if(!panel)continue;let first=-1;const entries=[...panel.querySelectorAll('.research-entry')],buttons=[...panel.querySelectorAll('.research-choice')];entries.forEach((entry,i)=>{const match=entry.textContent.toLowerCase().includes(q);buttons[i].hidden=!match;if(match){total++;if(first<0)first=i;}entry.classList.remove('selected');buttons[i].setAttribute('aria-pressed','false');});if(first>=0)buttons[first].click();}noResults.hidden=total>0;
 });
 // Show positive and negative realized results side by side, using a shared scale.
 renderProfitBars=function(){
  const host=$('#profit-bars');if(!host)return;
  const data=profitMode==='monthly'?PROFIT_MONTHLY_REAL:PROFIT_DATA;
  const max=Math.max(1,...data.map(d=>Math.abs(d.pnl)));
  host.classList.add('profit-comparison');host.replaceChildren();
  for(const positive of [true,false]){
   const rows=data.filter(d=>positive?d.pnl>=0:d.pnl<0).sort((a,b)=>Math.abs(b.pnl)-Math.abs(a.pnl));
   const sum=rows.reduce((a,d)=>a+d.pnl,0);
   const column=make('section','profit-column '+(positive?'positive':'negative'));
   column.innerHTML=`<header><h3>${positive?'실현 수익':'실현 손실'}</h3><strong class="${positive?'up':'dn'}">${sum>=0?'+':''}${fmt(Math.round(sum/10000))}만</strong></header>`;
   for(const d of rows){const row=make('div','profit-row');row.innerHTML=`<div class="profit-row-label"><span>${escape(d.name)}</span><strong class="${d.pnl>=0?'up':'dn'}">${d.pnl>=0?'+':''}${fmt(Math.round(d.pnl/10000))}만</strong></div><div class="profit-track"><div style="width:${Math.abs(d.pnl)/max*100}%"></div></div>`;column.append(row);}
   if(!rows.length)column.append(make('p','cl-subtle','해당 기록이 없습니다.'));
   host.append(column);
  }
 };
 const profitBlock=$('#profit-bars').closest('.port-block');profitBlock?.classList.add('profit-section');

})();
