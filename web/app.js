'use strict';
const $ = (q, root = document) => root.querySelector(q);
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const paths = {
  home:'M3 10 12 3l9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',
  review:'M7 3h10l3 3v15H4V3Zm1 6h8M8 13h8M8 17h5',
  library:'M3 5h7l2 3h9v12H3ZM7 12h10M7 16h6',
  evolution:'M4 7h13l-3-3m3 3-3 3M20 17H7l3 3m-3-3 3-3',
  graph:'M7 5h10M5 7v10M7 19h10M19 7v10M7 7l10 10M17 7 7 17M3 3h4v4H3ZM17 3h4v4h-4ZM3 17h4v4H3ZM17 17h4v4h-4Z',
  evaluation:'M4 19V9m5 10V5m5 14v-7m5 7V3M2 21h20',
  history:'M4 8a9 9 0 1 1-1 6M4 3v5h5M12 7v6l4 2',
  upload:'M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6',
  arrow:'M4 12h16m-6-6 6 6-6 6',
  shield:'M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7ZM8 12l3 3 5-6',
  company:'M4 21V6l10-3v18M14 10h6v11M8 8h2M8 12h2M8 16h2M17 13v2M2 21h20',
  search:'M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Zm6-2 6 6',
  link:'M9 15l6-6M7 17l-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0M17 7l1-1a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0',
  download:'M12 3v13m-5-5 5 5 5-5M4 16v5h16v-5',
};
const icon = name => `<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name] || paths.review}"/></svg>`;
const nav = [['home','工作台'],['review','企业预审'],['library','政策与材料'],['evolution','版本演进'],['graph','知识关联'],['evaluation','评测中心'],['history','运行记录']];
const state = {data:null,report:null,company:'demo-01',policy:'hnte-bj-2026',asOf:'',page:'home',asset:null};
const factNames = {city:'注册地',resident_enterprise:'居民企业身份',registration_date:'注册日期',employees:'职工总数',tech_staff:'科技人员数',allowed_industry:'行业范围核查',core_ip:'核心知识产权所有权',supported_domain:'高新技术领域归属',sme_compliance:'科技型中小企业信用与事故核查',hnte_compliance:'高企事故核查',ip_class1:'Ⅰ类知识产权数',ip_class2:'Ⅱ类知识产权数',fast_track:'有效直通车资格',sales:'销售收入',rd:'研发费用',domestic_rd:'境内研发费用',assets:'资产总额',cost:'成本费用',total_income:'总收入',hightech_income:'高新产品收入'};
const fieldName = key => { const m=key.match(/^(.*)_(20\d{2})$/); return m ? `${m[2]}年${factNames[m[1]]||m[1]}` : factNames[key]||key; };
const badge = (label, cls='') => `<span class="badge ${esc(cls)}">${esc(label)}</span>`;
const shortName = name => name.replace('（模拟）','');
const empty = (title, text, glyph='review') => `<div class="empty">${icon(glyph)}<strong>${esc(title)}</strong>${esc(text)}</div>`;

async function api(path, options={}) {
  if (options.body && !(options.body instanceof FormData)) options.headers={'Content-Type':'application/json',...options.headers};
  const res = await fetch(path,options);
  if(!res.ok){const body=await res.json().catch(()=>({detail:'请求失败'}));throw new Error(typeof body.detail==='string'?body.detail:JSON.stringify(body.detail));}
  return res.json();
}
function toast(text){$('#toast').textContent=text;$('#toast').style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').style.display='none',4500);}
async function refresh(){state.data=await api('/api/dashboard');if(!state.asOf)state.asOf=state.data.health.today;$('#today').textContent=state.data.health.today.replaceAll('-',' / ');}
function heading(title, text, actions=''){return `<div class="page-head"><div><h1>${title}</h1><p>${text}</p></div><div class="actions">${actions}</div></div>`;}
function companyOptions(){return state.data.companies.map(c=>`<option value="${esc(c.id)}" ${c.id===state.company?'selected':''}>${esc(c.name)}</option>`).join('');}
function policyOptions(){return state.data.policies.filter(p=>p.state==='current').map(p=>`<option value="${esc(p.id)}" ${p.id===state.policy?'selected':''}>${esc(p.name)} · ${p.year}</option>`).join('');}
function companyRows(){return state.data.companies.map((c,i)=>`<tr><td><div class="company-cell"><span class="company-logo">${esc(['研','数','制','软','创'][i%5])}</span><div><strong>${esc(shortName(c.name))}</strong><small>${esc(c.district)} · ${esc(c.industry)}</small></div></div></td><td>${badge(c.is_demo?'模拟案例':'用户导入',c.is_demo?'demo':'blue')}</td><td><button class="btn text" data-action="review-company" data-id="${esc(c.id)}">开始预审 ↗</button></td></tr>`).join('');}

function home(){
  const d=state.data, current=d.policies.filter(p=>p.state==='current');
  return heading('企业政策工作台','从政策条款到企业材料，让申报准备更清楚。',`<button class="btn" data-action="import-company">${icon('upload')}导入企业</button>`)+
  `<section class="hero"><div class="hero-copy"><div class="eyebrow">BEIJING · EVIDENCE FIRST</div><h2>每一次申报判断，<br>都能<em>找到依据。</em></h2><p>政策匹配 / 材料预审 / 变更复核，一处完成。</p><button class="btn primary" data-action="start-review">开始一次预审 ${icon('arrow')}</button></div><div class="hero-visual" aria-hidden="true"><div class="hero-orbit"></div><div class="paper"><div class="paper-top">企业申报材料<span>2026</span></div><div class="paper-line"></div><div class="paper-line short"></div><div class="paper-line"></div><div class="paper-row"><span class="paper-check">✓</span>关联政策条款</div><div class="paper-row"><span class="paper-check">✓</span>核对材料与期间</div><div class="paper-row"><span class="paper-check">✓</span>保留判断依据</div></div><div class="floating-proof"><span class="proof-symbol">✓</span><div>证据链可追溯<small>政策 → 条件 → 材料 → 结论</small></div></div></div></section>
  <div class="stats">${[[current.length,'覆盖申报事项','北京地区 · 2026 申报季','review','项'],[d.sources.length,'官方来源','保留来源与抓取记录','library','份'],[d.companies.length,'企业案例','内置案例均为模拟数据','company','家'],[d.reports.length,'已保存预审','每份报告保留输入快照指纹','shield','份']].map(([n,label,note,g,unit])=>`<div class="stat"><div><div class="stat-label">${label}</div><div class="stat-value">${n}<small>${unit}</small></div><div class="stat-note">${note}</div></div><div class="stat-icon">${icon(g)}</div></div>`).join('')}</div>
  <div class="columns"><section class="card"><div class="card-head"><h2>从一份企业案例开始</h2><small>覆盖完整、缺失与冲突材料</small></div><div class="table-wrap"><table><thead><tr><th>企业</th><th>数据性质</th><th>操作</th></tr></thead><tbody>${companyRows()}</tbody></table></div><div class="table-caption">数量条件核查与受理窗口分别判断，材料不足时保留待核验状态。</div></section>
  <div><section class="card"><div class="card-head"><h2>当前申报窗口</h2><small>${esc(d.health.today)}</small></div>${current.map(p=>`<div class="policy-item"><h3>${esc(p.name)} ${badge(p.window.status==='open'?'受理期内':'填报已截止',p.window.status)}</h3><p>${esc(p.description)}</p><div class="policy-meta"><span>截止 ${esc(p.deadlines.at(-1))}</span><a href="${esc(p.source.url)}" target="_blank" rel="noopener noreferrer">官方通知 ↗</a></div></div>`).join('')}</section><div class="callout">${icon('evolution')}<div><strong>政策变了，哪些判断需要重看？</strong><br>对比 2025 与 2026 申报季，定位日期和资料期间变化。<br><a href="#evolution">查看版本演进 →</a></div></div><div class="intro-line">${icon('shield')}当前提供材料预审，不代替资格认定。</div></div></div>`;
}

function reviewPage(){
  const r=state.report;
  const total=r?Object.values(r.counts).reduce((sum,value)=>sum+Number(value||0),0):0;
  const decided=r?Number(r.counts.pass||0)+Number(r.counts.fail||0)+Number(r.counts.conflict||0):0;
  const q=r?.quality||{decision_coverage:total?decided/total:0,evidence_coverage:0,traceability_rate:0,automation_scope:0};
  return heading('企业材料预审','逐项核对政策要求，保留计算过程与材料出处。',`<button class="btn" data-action="edit-company">${icon('company')}核对企业资料</button>`)+
    `<section class="card"><div class="card-body"><form id="review-form" class="form-row"><div class="form-group"><label for="company-select">企业案例</label><select id="company-select">${companyOptions()}</select></div><div class="form-group"><label for="policy-select">申报事项</label><select id="policy-select">${policyOptions()}</select></div><div class="form-group"><label for="as-of">核查日期</label><input type="date" id="as-of" value="${esc(state.asOf)}" required></div><button type="submit" class="btn primary" id="run-review">${icon('shield')}执行预审</button></form></div></section>`+
    (!r?`<section class="card">${empty('开始核对企业材料','选择企业、事项和日期后执行预审。无需模型密钥即可验证规则和证据。')}</section>`:
    `<section class="card"><div class="review-summary"><div class="summary-main">${badge(r.is_demo?'模拟企业 · 模拟材料':'用户提供材料',r.is_demo?'demo':'blue')}<h2>${esc(r.status_label)}</h2><p>${esc(r.company_name)}<br>${esc(r.policy_name)} · ${esc(r.as_of)}</p></div><div class="summary-count" style="color:var(--green)">${r.counts.pass}<small>已核对满足</small></div><div class="summary-count" style="color:var(--red)">${r.counts.fail+r.counts.conflict}<small>不满足 / 冲突</small></div><div class="summary-count" style="color:var(--amber)">${r.counts.unknown}<small>待补证复核</small></div></div></section>
    <div class="callout ${r.window.status==='open'?'':'amber'}">${icon('history')}<div><strong>受理窗口：${esc(r.window.label)}</strong>${r.window.next_deadline?` · 最近批次截止 ${esc(r.window.next_deadline)}`:''}<br>${esc(r.disclaimer)} <a href="${esc((r.window.source||state.data.policies.find(p=>p.id===r.policy_id).source).url)}" target="_blank" rel="noopener noreferrer">查看通知 ↗</a></div></div><div class="spacer"></div>
    <section class="quality-strip"><div><strong>${(q.decision_coverage*100).toFixed(0)}%</strong><span>决策覆盖率</span></div><div><strong>${(q.evidence_coverage*100).toFixed(0)}%</strong><span>材料证据覆盖率</span></div><div><strong>${(q.traceability_rate*100).toFixed(0)}%</strong><span>已决检查可追溯率</span></div><div><strong>${(q.automation_scope*100).toFixed(0)}%</strong><span>当前自动化范围</span></div></section><div class="spacer"></div>
    <div class="columns"><section class="card"><div class="card-head"><h2>条件核查明细</h2><small>点击条目展开证据</small></div>${r.checks.map((c,i)=>`<div class="rule-item"><button class="rule-row" data-action="toggle-rule" data-index="${i}" aria-expanded="false"><span class="rule-name"><span class="status-icon ${c.status}">${c.status==='pass'?'✓':c.status==='unknown'?'?':'!'}</span><span><strong>${esc(c.title)}</strong><small>${esc(c.clause)}</small></span></span><span class="rule-right">${badge(c.status_label,c.status)}<span>⌄</span></span></button><div id="rule-${i}" class="rule-detail hidden">${checkDetail(c)}</div></div>`).join('')}</section>
    <div><section class="card"><div class="card-head"><h2>补证与复核清单</h2>${badge(r.missing_fields.length+' 项','blue')}</div><div class="card-body">${r.missing_fields.length?`<ul class="list-clean">${r.missing_fields.map(k=>`<li>${esc(fieldName(k))}<button class="btn text" style="float:right" data-action="edit-fact" data-field="${esc(k)}">核对 →</button></li>`).join('')}</ul>`:'<p class="muted" style="font-size:12px">已实现指标暂无缺失字段，仍需核验下列业务事项。</p>'}<div class="spacer"></div><div class="section-title">仍需人工核验</div><ul class="list-clean">${r.manual_checks.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div></section><section class="card"><div class="card-body"><div class="section-title">保存完整判断依据</div><p class="muted" style="font-size:11px;line-height:1.8">报告包含条款、材料位置、计算过程和快照指纹。</p><div class="actions"><a class="btn primary" href="/api/reviews/${r.id}/report.md">${icon('download')}导出报告</a><a class="btn" href="#graph">${icon('graph')}证据关联</a></div></div></section></div></div>`);
}

function checkDetail(c){return `<p>${esc(c.reasoning)}</p><div class="quote">${esc(c.quote)}<br><a class="source-link" href="${esc(c.source.url)}" target="_blank" rel="noopener noreferrer">${esc(c.source.title)} ↗</a></div>${c.evidence.map(e=>`<div class="evidence-card"><strong>${esc(e.title)}</strong><p>${esc(e.text)}</p><small>${esc(e.locator)}${e.asset_id?` · <a href="/api/assets/${encodeURIComponent(e.asset_id)}/file">原始材料 ↓</a>`:''}</small></div>`).join('')}${!c.evidence.length?'<p class="muted">本项尚无可用企业材料。</p>':''}`;}

function library(){
  const d=state.data;
  return heading('政策与材料','原始材料保留来源；提取候选经你确认后才进入企业事实或概念库。',`<a class="btn" href="/api/template/financial.csv">${icon('download')}下载补证示例</a>`)+
  `<div class="upload-grid"><section class="card" style="margin:0"><div class="card-body"><div class="form-group" style="margin-bottom:15px"><label for="upload-purpose">资料用途</label><select id="upload-purpose"><option value="company">企业材料 · 提取待核对字段</option><option value="policy">政策资料 · 提取概念候选</option></select></div><label class="upload-zone" id="drop-zone" for="asset-file">${icon('upload')}<strong>点击上传，或将文件拖到这里</strong><small>PDF / DOCX / XLSX / CSV / TXT / PNG / JPG · 单份不超过 12 MB<br>PNG/JPG 可用本地 OCR 生成待核对草稿；扫描 PDF 需先逐页转成图片。</small><input class="hidden" id="asset-file" type="file" accept=".pdf,.docx,.xlsx,.csv,.txt,.md,.png,.jpg,.jpeg"></label></div></section><section class="card" style="margin:0"><div class="card-head"><h2>查找政策依据</h2></div><div class="card-body"><form class="searchbar" id="search-form"><input id="search-q" placeholder="例如：研发费用、人员比例" aria-label="搜索政策"><button class="btn primary">检索</button></form><div id="search-results"><div class="intro-line">${icon('link')}返回条款与资料中的具体位置</div></div></div></section></div>
  <section class="card"><div class="card-head"><h2>已导入材料</h2><small>${d.assets.length} 份 · 内容指纹去重</small></div>${d.assets.length?`<div class="table-wrap"><table><thead><tr><th>材料名称</th><th>用途</th><th>状态</th><th>待确认候选</th><th></th></tr></thead><tbody>${d.assets.map(a=>`<tr><td>${esc(a.filename)}<small>${(a.bytes/1024).toFixed(1)} KB · SHA-256 ${a.sha256.slice(0,12)}…</small></td><td>${a.purpose==='company'?'企业材料':'政策资料'}</td><td>${badge(a.status==='parsed'?'已解析':a.status==='ocr_draft'?'识别草稿 · 待核对':'待图片识别',a.status==='parsed'?'pass':'unknown')}</td><td>${a.proposals.filter(p=>p.state==='pending').length}</td><td><button class="btn text" data-action="view-asset" data-id="${a.id}">查看与核对 →</button></td></tr>`).join('')}</tbody></table></div>`:empty('还没有上传材料','可下载补证示例，导入后给“青芽数据”补充缺失的 2024 年研发费用。','upload')}</section>
  <section class="card"><div class="card-head"><h2>官方政策来源</h2><small>本地收录快照，非实时政策监测</small></div><div class="table-wrap"><table><thead><tr><th>文件</th><th>发布单位</th><th>归档</th><th>出处</th></tr></thead><tbody>${d.sources.map(s=>`<tr><td>${esc(s.title)}<small>${esc(s.published)}${s.retrieved_at?' · 收录 '+esc(s.retrieved_at.slice(0,10)):''}</small></td><td>${esc(s.authority)}</td><td>${badge(s.status==='cached'?'已归档':'待归档',s.status==='cached'?'pass':'unknown')}</td><td><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">官方原文 ↗</a></td></tr>`).join('')}</tbody></table></div></section>`;
}

async function evolution(){
  const diff=await api(`/api/compare?as_of=${encodeURIComponent(state.asOf)}`);
  const old=state.data.policies.find(p=>p.id===diff.old), fresh=state.data.policies.find(p=>p.id===diff.new);
  return heading('政策版本演进','比较真实申报季，区分日期变化、资料期间变化和认定门槛变化。')+
  `<div class="version-grid"><div class="version-card">${badge('历史申报季')}<h3>2025 科技型中小企业评价</h3><p>开放：${old.start}<br>截止：${old.deadlines.join('、')}<br>主要财务资料年度：2024</p><a class="source-link" href="${esc(old.source.url)}" target="_blank" rel="noopener noreferrer">官方原文 ↗</a></div><div class="version-arrow">→</div><div class="version-card new">${badge('当前收录版本','blue')}<h3>2026 科技型中小企业评价</h3><p>开放：${fresh.start}<br>截止：${fresh.deadlines.join('、')}<br>主要财务资料年度：2025</p><a class="source-link" href="${esc(fresh.source.url)}" target="_blank" rel="noopener noreferrer">官方原文 ↗</a></div></div><div class="callout">${icon('evolution')}<div>${esc(diff.note)}<br>当前比较日期：${esc(diff.as_of)}；可在企业预审中更换核查日期。</div></div><div class="spacer"></div>
  <section class="card"><div class="card-head"><h2>配置变化</h2>${badge(diff.changes.length+' 处','blue')}</div><div class="card-body">${diff.changes.map(c=>`<div class="proposal"><div class="section-title">${esc(c.label)}</div><div class="diff"><div>${esc(typeof c.before==='object'?JSON.stringify(c.before,null,2):c.before)}</div><div>${esc(typeof c.after==='object'?JSON.stringify(c.after,null,2):c.after)}</div></div></div>`).join('')}</div></section>
  <section class="card"><div class="card-head"><h2>关联企业复核</h2><small>针对新的资料期间重算</small></div><div class="table-wrap"><table><thead><tr><th>企业</th><th>旧版本核查</th><th>新版本核查</th><th>新版本窗口</th><th></th></tr></thead><tbody>${diff.impacts.map(c=>`<tr><td>${esc(c.company_name)}</td><td>${esc(c.before_status)}</td><td>${esc(c.after_status)}</td><td>${esc(c.after_window)}</td><td><button class="btn text" data-action="review-company-sme" data-id="${c.company_id}">重新预审 →</button></td></tr>`).join('')}</tbody></table></div></section>`;
}

async function evaluationPage(){
  const [result,publicNotice]=await Promise.all([api('/api/evaluation'),api('/api/evaluation/public-notice')]),engine=result.engine,es=engine.summary,baseline=result.llm_baseline,bs=baseline?.summary,ps=publicNotice.summary;
  const pct=v=>`${(Number(v||0)*100).toFixed(1)}%`;
  return heading('评测中心','使用同一组政策规则与模拟企业事实，对困难案例进行可复现测试。')+
  `<div class="callout">${icon('evaluation')}<div><strong>${esc(result.dataset.name)}</strong><br>${esc(result.dataset.data_type)}；${esc(result.dataset.leakage_note)}</div></div><div class="spacer"></div>
  <div class="stats"><div class="stat"><div><div class="stat-label">困难案例</div><div class="stat-value">${es.case_count}<small>项</small></div><div class="stat-note">${Object.keys(es.categories).length} 类边界与异常情形</div></div></div><div class="stat"><div><div class="stat-label">规则状态准确率</div><div class="stat-value">${pct(es.status_accuracy)}</div><div class="stat-note">${es.status_correct}/${es.case_count} 项状态判断正确</div></div></div><div class="stat"><div><div class="stat-label">缺失字段准确率</div><div class="stat-value">${pct(es.missing_field_accuracy)}</div><div class="stat-note">精确匹配待补字段集合</div></div></div><div class="stat"><div><div class="stat-label">引擎总耗时</div><div class="stat-value">${engine.total_latency_ms.toFixed(1)}<small>ms</small></div><div class="stat-note">本机确定性批量执行</div></div></div></div>
  <div class="columns"><section class="card"><div class="card-head"><h2>逐案例结果</h2><small>结果来自 artifacts/evaluation-results.json</small></div><div class="table-wrap"><table><thead><tr><th>案例</th><th>类别</th><th>预期</th><th>引擎结果</th><th>结果</th></tr></thead><tbody>${engine.cases.map(c=>`<tr><td>${esc(c.description)}<small class="mono">${esc(c.id)}</small></td><td>${esc(c.category)}</td><td>${badge(c.expected_status,c.expected_status)}</td><td>${badge(c.predicted_status,c.predicted_status)}</td><td>${c.score.exact?badge('精确匹配','pass'):badge('不匹配','fail')}</td></tr>`).join('')}</tbody></table></div></section>
  <div><section class="card"><div class="card-head"><h2>单模型消融</h2></div><div class="card-body">${baseline?`<p><strong>${esc(baseline.name)}</strong></p><div class="metric-line"><span>状态准确率</span><strong>${pct(bs.status_accuracy)}</strong></div><div class="metric-line"><span>缺失字段准确率</span><strong>${pct(bs.missing_field_accuracy)}</strong></div><div class="metric-line"><span>总耗时</span><strong>${(baseline.total_latency_ms/1000).toFixed(1)} 秒</strong></div>`:`<p class="muted">尚未运行本地单模型消融。执行评测脚本后，这里会显示同输入条件下的实测对比。</p>`}</div></section><section class="card"><div class="card-head"><h2>公开记录：资料不足时的拒判</h2></div><div class="card-body"><div class="metric-line"><span>官方公示记录</span><strong>${ps.record_count} 条</strong></div><div class="metric-line"><span>未臆断预审通过</span><strong>${ps.abstained_count}/${ps.record_count}</strong></div><div class="metric-line"><span>已授权企业案例</span><strong>0 家</strong></div><p class="muted" style="line-height:1.8">${esc(publicNotice.dataset.claim_boundary)}</p></div></section><section class="card"><div class="card-body"><div class="section-title">指标边界</div><p class="muted" style="line-height:1.8">模拟困难案例与公开公示记录是两种不同数据。前者验证规则边界，后者验证材料不足时拒绝臆断；两者都不代表真实企业申报通过率。真实脱敏案例仍需授权和业务专家复核。</p></div></section></div></div>`;
}

function graphPage(){
  const r=state.report;
  let graph='';
  if(r){
    const sources=[...new Map(r.checks.map(c=>[c.source.id,c.source])).values()];
    const h=Math.max(440,r.checks.length*64+90), nodeY=i=>65+i*64;
    const sourceY=i=>90+i*(h-170)/Math.max(1,sources.length-1);
    let edges='',nodes='';
    for(let i=0;i<r.checks.length;i++){
      const c=r.checks[i],sy=sourceY(sources.findIndex(s=>s.id===c.source.id)),y=nodeY(i),col=c.status==='pass'?'#edf8f3':c.status==='unknown'?'#fff7eb':'#fff0f1';
      edges+=`<path class="graph-edge" d="M205 ${sy+24} C265 ${sy+24} 270 ${y+23} 320 ${y+23}"/><path class="graph-edge" d="M565 ${y+23} C650 ${y+23} 650 ${h/2} 735 ${h/2}"/>`;
      nodes+=`<g class="graph-node" data-action="graph-rule" data-index="${i}" tabindex="0" role="button" aria-label="${esc(c.title)}"><rect x="320" y="${y}" width="245" height="46" rx="7" fill="${col}" stroke="#e6ebf4"/><text x="336" y="${y+19}" class="graph-title">${esc(c.title)}</text><text x="336" y="${y+35}" style="font-size:9px;fill:#8d9ab0">${c.evidence.length} 处材料 · ${esc(c.status_label)}</text></g>`;
    }
    nodes+=sources.map((s,i)=>`<g><rect x="15" y="${sourceY(i)}" width="190" height="53" rx="7" fill="#f1f5fe" stroke="#dce5f7"/><text x="29" y="${sourceY(i)+22}" class="graph-title">${s.id.includes('national')?'国家认定 / 评价办法':'北京年度申报通知'}</text><text x="29" y="${sourceY(i)+39}" style="font-size:9px;fill:#91a0b9">${esc(s.id)}</text></g>`).join('');
    graph=`<div class="graph-wrap"><svg class="graph-svg" viewBox="0 0 960 ${h}" role="img" aria-label="政策规则、材料与预审结论的证据关联图"><text x="15" y="28" class="graph-label">政策来源</text><text x="320" y="28" class="graph-label">规则与材料 · 点击查看依据</text><text x="735" y="28" class="graph-label">预审结果</text>${edges}${nodes}<rect class="graph-end" x="735" y="${h/2-37}" width="200" height="74" rx="11"/><text x="750" y="${h/2-5}" class="graph-title">${esc(r.status_label)}</text><text x="750" y="${h/2+17}" style="font-size:10px;fill:#8c9bb5">${esc(r.as_of)} · 待业务复核</text></svg><div class="legend"><span><i style="background:#72b5a2"></i>已核对满足</span><span><i style="background:#dab575"></i>待补证</span><span><i style="background:#da8f99"></i>不满足 / 冲突</span><span>连线表示判断依赖，不代表因果关系。</span></div></div>`;
  }
  return heading('知识与证据关联','查看本次预审实际使用的政策、规则和材料。')+`<section class="card"><div class="card-head"><h2>${r?esc(r.company_name):'预审证据图'}</h2>${r?badge(r.policy_name,'blue'):''}</div>${r?graph:empty('先执行一次企业预审','证据图由实际判断记录生成，不展示预设的虚构关系。','graph')}</section><section class="card"><div class="card-head"><h2>人工确认的领域概念</h2><small>从政策材料中提取候选；确认概念不等于自动发布规则</small></div>${state.data.ontology.length?`<div class="table-wrap"><table><thead><tr><th>原文术语</th><th>对齐字段</th><th>来源片段</th></tr></thead><tbody>${state.data.ontology.map(o=>`<tr><td>${esc(o.term)}</td><td>${esc(fieldName(o.canonical_field))}</td><td>${esc(o.quote)}<small>${esc(o.locator)}</small></td></tr>`).join('')}</tbody></table></div>`:empty('尚无新增概念','在“政策与材料”上传政策文档，核对概念候选后加入领域概念库。','library')}</section>`;
}

async function history(){
  const events=await api('/api/events');
  const labels={review:'执行预审',company_import:'导入企业',fact_update:'人工核对事实',asset_import:'导入材料',proposal_accept:'确认提取候选'};
  return heading('运行记录','每次预审保留输入与规则指纹，材料修改和人工确认可回看。')+`<section class="card"><div class="card-head"><h2>已保存的预审报告</h2></div>${state.data.reports.length?`<div class="table-wrap"><table><thead><tr><th>企业与事项</th><th>日期</th><th>结果</th><th>快照</th><th></th></tr></thead><tbody>${state.data.reports.map(r=>`<tr><td>${esc(r.company_name)}<small>${esc(r.policy_name)}</small></td><td>${esc(r.as_of)}</td><td>${badge(r.status_label,r.status)}</td><td class="mono">${r.fingerprint.slice(0,12)}…</td><td><button class="btn text" data-action="open-report" data-id="${r.id}">查看报告 →</button></td></tr>`).join('')}</tbody></table></div>`:empty('暂无报告','完成一次预审后，报告会保存在本机。')}</section><section class="card"><div class="card-head"><h2>最近操作</h2><small>最多显示 100 条</small></div><div class="table-wrap"><table><thead><tr><th>操作</th><th>对象</th><th>时间</th></tr></thead><tbody>${events.map(e=>`<tr><td>${esc(labels[e.action]||e.action)}</td><td class="mono">${esc(e.target)}</td><td>${esc(new Date(e.created_at).toLocaleString('zh-CN'))}</td></tr>`).join('')}</tbody></table></div></section>`;
}

async function render(){
  const page=location.hash.slice(1)||'home';state.page=nav.some(n=>n[0]===page)?page:'home';
  $('#nav').innerHTML=nav.map(([id,label])=>`<a href="#${id}" ${id===state.page?'class="active" aria-current="page"':''}>${icon(id)}${label}</a>`).join('');
  $('#breadcrumb').textContent=nav.find(n=>n[0]===state.page)[1];
  try{
    const content=await ({home,review:reviewPage,library,evolution,graph:graphPage,evaluation:evaluationPage,history}[state.page])();
    $('#main').innerHTML=content;
    bindForms();
  }catch(error){$('#main').innerHTML=empty('暂时无法加载',error.message);}
}

async function executeReview(){
  const button=$('#run-review');if(button){button.disabled=true;button.textContent='正在核对…';}
  try{state.report=await api('/api/reviews',{method:'POST',body:JSON.stringify({company_id:state.company,policy_id:state.policy,as_of:state.asOf})});await refresh();await render();toast('预审完成，证据与报告已保存');}
  catch(error){toast(error.message);if(button){button.disabled=false;button.textContent='执行预审';}}
}
function dialog(title, body, foot=''){$('#dialog-content').innerHTML=`<div class="dialog-head"><h2>${title}</h2><button class="close" data-action="close-dialog" aria-label="关闭">×</button></div><div class="dialog-body">${body}</div>${foot?`<div class="dialog-foot">${foot}</div>`:''}`;if(!$('#dialog').open)$('#dialog').showModal();}
function editCompany(){const c=state.data.companies.find(c=>c.id===state.company);dialog('核对企业资料',`<p class="muted">${esc(c.name)} · 每个已确认事实都关联一条材料记录。</p><div class="table-wrap"><table><thead><tr><th>字段</th><th>值 / 期间</th><th>状态</th><th></th></tr></thead><tbody>${Object.entries(c.facts).map(([k,f])=>`<tr><td>${esc(fieldName(k))}</td><td>${esc(f.value)} ${esc(f.unit)}<small>${esc(f.period)}</small></td><td>${badge(f.status==='confirmed'?'已人工核对':f.status==='conflict'?'冲突':'待核对',f.status==='confirmed'?'pass':'unknown')}</td><td><button class="btn text" data-action="edit-fact" data-field="${esc(k)}">核对</button></td></tr>`).join('')}</tbody></table></div>`);}
function editFact(field){
  const c=state.data.companies.find(c=>c.id===state.company),f=c.facts[field]||{value:'',unit:field.match(/_(20\d{2})$/)?'万元':'',period:field.match(/_(20\d{2})$/)?.[1]||''};
  dialog('核对：'+esc(fieldName(field)),`<form id="fact-form" data-field="${esc(field)}"><div class="field-grid"><div class="form-group"><label>数值 / 内容（布尔值填 true 或 false）</label><input id="fact-value" value="${esc(f.value)}" required></div><div class="form-group"><label>单位</label><input id="fact-unit" value="${esc(f.unit)}" placeholder="万元 / 人 / 项"></div><div class="form-group"><label>所属期间</label><input id="fact-period" value="${esc(f.period)}" placeholder="例如 2025"></div><div class="form-group wide"><label>核对依据与处理说明</label><textarea id="fact-note" rows="3" required placeholder="请写明材料名称、页码或行号，以及如何确认该值。"></textarea></div></div><label class="check-label"><input type="checkbox" id="fact-confirmed">我已对照材料核实该字段</label><div class="spacer"></div><button class="btn primary" type="submit">保存核对记录</button></form>`);
  $('#fact-form').onsubmit=async e=>{e.preventDefault();let value=$('#fact-value').value.trim();if(value==='true'||value==='false')value=value==='true';else if(/^-?\d+(\.\d+)?$/.test(value))value=Number(value);try{await api(`/api/companies/${encodeURIComponent(state.company)}/facts/${encodeURIComponent(field)}`,{method:'PATCH',body:JSON.stringify({value,unit:$('#fact-unit').value.trim(),period:$('#fact-period').value.trim(),confirmed:$('#fact-confirmed').checked,note:$('#fact-note').value.trim()})});$('#dialog').close();state.report=null;await refresh();await render();toast('材料已更新，请重新执行预审');}catch(error){toast(error.message);}};
}
function importCompany(){dialog('导入企业案例',`<p class="muted" style="line-height:1.9">使用结构化模板导入企业资料。请为每个确认值保留材料证据；真实企业将 is_demo 改为 false，并使用新的企业 id。</p><a class="btn" href="/api/template/company.json">${icon('download')}下载完整模板</a><div class="spacer"></div><input type="file" id="company-file" accept=".json" aria-label="选择企业 JSON 文件"><div class="spacer"></div><div class="callout">导入会创建新的企业记录，重复 ID 不会覆盖已有材料。</div>`);$('#company-file').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{const c=JSON.parse(await f.text());await api('/api/companies',{method:'POST',body:JSON.stringify(c)});await refresh();$('#dialog').close();await render();toast('企业已导入');}catch(error){toast(error.message);}};}
async function upload(file){if(!file)return;const form=new FormData();form.append('file',file);form.append('purpose',$('#upload-purpose').value);toast('正在解析材料…');try{const a=await api('/api/assets',{method:'POST',body:form});await refresh();await render();await viewAsset(a.id);}catch(error){toast(error.message);}}
async function viewAsset(id){
  const a=await api('/api/assets/'+encodeURIComponent(id));state.asset=a;
  dialog(esc(a.filename),`<div class="actions">${badge(a.purpose==='company'?'企业字段候选':'领域概念候选','blue')}${badge(a.status==='parsed'?'已解析':a.status==='ocr_draft'?'识别草稿 · 待核对':'待图片识别',a.status==='parsed'?'pass':'unknown')}<a class="btn small" href="/api/assets/${a.id}/file">原始文件 ↓</a></div>${a.purpose==='company'?`<div class="form-group" style="margin-top:20px"><label>把核对后的字段关联到企业</label><select id="proposal-company">${companyOptions()}</select></div>`:''}<p class="muted" style="font-size:12px;line-height:1.9">${a.purpose==='company'?'确认前请对照下面的原文片段。与已有事实不一致时，系统保留冲突，需再次人工核对。':'当前按种子术语提取概念候选。确认后加入概念库，不会自动改写政策门槛。'}</p>${a.proposals.length?a.proposals.map(p=>`<div class="proposal"><div class="proposal-top"><strong>${esc(p.field?fieldName(p.field):p.term)}</strong>${p.state==='pending'?`<button class="btn small primary" data-action="accept-proposal" data-id="${p.id}">确认候选</button>`:badge('已确认','pass')}</div><p>${p.field?`值：${esc(p.value)} ${esc(p.unit)} · 期间：${esc(p.period||'未标注')}`:`对齐字段：${esc(fieldName(p.canonical_field))}`}</p><pre>${esc(p.quote)}</pre><small class="muted">${esc(p.locator)}</small></div>`).join(''):empty(a.status==='pending_ocr'?'原件已保留，尚未识别':'未找到可直接确认的字段',a.status==='pending_ocr'?'PNG/JPG 可点击“本地 OCR 识别”；草稿需对照原图确认，扫描 PDF 请先转图片。':'可使用“字段,数值,单位,期间”的表格，或在企业资料中手动核对。')}<details style="margin-top:22px"><summary class="muted" style="cursor:pointer">查看已提取正文</summary>${a.chunks.slice(0,30).map(c=>`<div class="evidence-card"><strong>${esc(c.locator)}</strong><p>${esc(c.text)}</p></div>`).join('')}</details>`);
  if(a.purpose==='policy'){
    $('#dialog-content .dialog-body').insertAdjacentHTML('beforeend',`<div class="proposal"><strong>政策阈值变化预览</strong><p class="muted">从同一条款中的术语、比较词、数值和单位提出候选。结果仅模拟影响，必须核验政策权威性、有效期和上下文。</p><div class="actions"><select id="change-policy" aria-label="比较的政策版本">${state.data.policies.map(p=>`<option value="${esc(p.id)}">${esc(p.name)} · ${esc(p.year)}</option>`).join('')}</select><button class="btn small" data-action="preview-policy-change">提取候选并预览影响</button></div><div id="change-preview"></div></div>`);
    $('#change-policy').value=state.policy;
  }
  if(['.png','.jpg','.jpeg'].includes(a.suffix)){
    if(a.status==='pending_ocr'){
      const button=document.createElement('button');button.className='btn small';button.dataset.action='local-ocr';button.dataset.id=a.id;button.textContent='本地 OCR 识别';
      $('#dialog-content .actions').append(button);
    }else if(a.status==='ocr_draft'){
      $('#dialog-content .dialog-body').insertAdjacentHTML('beforeend','<label class="check-label"><input type="checkbox" id="visual-verified">我已打开原图并逐项核对识别内容</label>');
    }
  }
  const s=$('#proposal-company');if(s)s.onchange=()=>state.company=s.value;
  if(a.status==='ocr_draft')$('#dialog-content .actions .badge:nth-child(2)').textContent='识别草稿 · 待核对';
  if(a.purpose==='company'){
    const button=document.createElement('button');button.className='btn small';button.dataset.action='model-extract';button.dataset.id=a.id;
    button.textContent=state.data.health.model_configured?'使用模型提取候选':'识别模型待配置';button.disabled=!state.data.health.model_configured;
    $('#dialog-content .actions').append(button);
    if(state.data.health.model_configured){const note=document.createElement('p');note.className='muted';note.style.fontSize='11px';note.textContent='点击模型提取会将这份材料发送到你在本地配置的模型服务，结果仍需人工核对。';$('#dialog-content .actions').after(note);}
  }
}

function bindForms(){
  const form=$('#review-form');if(form){form.onsubmit=e=>{e.preventDefault();state.company=$('#company-select').value;state.policy=$('#policy-select').value;state.asOf=$('#as-of').value;executeReview();};for(const id of ['company-select','policy-select','as-of'])$('#'+id).onchange=()=>{state.company=$('#company-select').value;state.policy=$('#policy-select').value;state.asOf=$('#as-of').value;state.report=null;render();};}
  const input=$('#asset-file');if(input)input.onchange=e=>upload(e.target.files[0]);
  const zone=$('#drop-zone');if(zone){zone.ondragover=e=>{e.preventDefault();zone.style.borderColor='#365dea';};zone.ondragleave=()=>zone.style.borderColor='';zone.ondrop=e=>{e.preventDefault();zone.style.borderColor='';upload(e.dataTransfer.files[0]);};}
  const search=$('#search-form');if(search)search.onsubmit=async e=>{e.preventDefault();try{const result=await api('/api/search?q='+encodeURIComponent($('#search-q').value));$('#search-results').innerHTML=result.results.length?result.results.map(r=>`<div class="search-result"><strong style="font-size:12px">${esc(r.title)}</strong><p>${esc(r.text.slice(0,300))}</p><small class="muted">${esc(r.locator)} ${r.url?`<a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">原文 ↗</a>`:''}</small></div>`).join(''):empty('未找到匹配片段','尝试使用更具体的政策术语。','search');}catch(error){toast(error.message);}};
}

document.addEventListener('click',async e=>{
  const el=e.target.closest('[data-action]');if(!el)return;
  const {action,id,field,index}=el.dataset;
  try{
    if(action==='close-dialog')$('#dialog').close();
    if(action==='import-company')importCompany();
    if(action==='edit-company')editCompany();
    if(action==='edit-fact')editFact(field);
    if(action==='start-review'||action==='review-company'||action==='review-company-sme'){
      if(id)state.company=id;if(action==='review-company-sme')state.policy='sme-bj-2026';state.report=null;
      if(location.hash!=='#review')location.hash='review';else await render();
    }
    if(action==='toggle-rule'){const d=$('#rule-'+index);d.classList.toggle('hidden');el.setAttribute('aria-expanded',String(!d.classList.contains('hidden')));}
    if(action==='graph-rule')dialog(esc(state.report.checks[index].title),checkDetail(state.report.checks[index]));
    if(action==='view-asset')await viewAsset(id);
    if(action==='model-extract'){el.disabled=true;el.textContent='正在提取…';await api(`/api/assets/${id}/model-extract`,{method:'POST'});await refresh();await render();await viewAsset(id);toast('模型提取完成，候选待人工核对');}
    if(action==='local-ocr'){el.disabled=true;el.textContent='正在识别…';await api(`/api/assets/${id}/ocr`,{method:'POST'});await refresh();await render();await viewAsset(id);toast('OCR 草稿已生成，请对照原图核查');}
    if(action==='preview-policy-change'){
      el.disabled=true;
      const result=await api('/api/policy-change-preview?'+new URLSearchParams({asset_id:state.asset.id,policy_id:$('#change-policy').value,as_of:state.asOf}));
      $('#change-preview').innerHTML=result.candidates.length?result.candidates.map(c=>`<div class="evidence-card"><strong>${esc(c.rule_title)}</strong><p>${esc(c.current_threshold)} → ${esc(c.candidate_threshold)} ${esc(c.unit)} · ${c.changed?'待核验变化':'与现行配置一致'} · 影响 ${c.affected_count} 家演示/导入企业</p><small>${esc(c.locator)}：${esc(c.quote)}</small>${c.affected_companies.map(x=>`<p class="muted">${esc(x.company_name)}：${esc(x.rule_before)} → ${esc(x.rule_after)}${x.is_demo?'（模拟）':''}</p>`).join('')}</div>`).join(''):empty('未发现可安全对齐的数值门槛','请核对政策原文；系统不会根据模糊语句猜测规则变化。');
      el.disabled=false;
    }
    if(action==='accept-proposal'){el.disabled=true;await api(`/api/assets/${state.asset.id}/proposals/${id}/accept`,{method:'POST',body:JSON.stringify({company_id:state.asset.purpose==='company'?$('#proposal-company').value:null,visual_verified:$('#visual-verified')?.checked||false})});state.report=null;await refresh();await render();if($('#dialog').open)await viewAsset(state.asset.id);toast('候选已确认，相关企业请重新预审');}
    if(action==='open-report'){state.report=await api('/api/reviews/'+id);state.company=state.report.company_id;state.policy=state.report.policy_id;state.asOf=state.report.as_of;location.hash='review';}
  }catch(error){toast(error.message);if(el.tagName==='BUTTON')el.disabled=false;}
});
document.addEventListener('keydown',e=>{if((e.key==='Enter'||e.key===' ')&&e.target.matches('.graph-node')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
$('#dialog').addEventListener('click',e=>{if(e.target===$('#dialog'))$('#dialog').close();});
window.addEventListener('hashchange',render);
refresh().then(render).catch(e=>{$('#main').innerHTML=empty('服务尚未就绪',e.message);});
