/** Import Excel/CSV/JSON. Semua penulisan dilindungi lock, sandaran dan jurnal pemulihan. */
const IMPORT_LOG_=['import_id','masa_import','kuat_kuasa','label','status','sandaran_json','dibatalkan_json','ringkasan_json'];
const IMPORT_JADUAL_=['jadual_id','guru_id','nama_guru','hari_no','hari','waktu','masa_mula','masa_tamat','subjek_label','kelas_label','bilik_label','blok_id','halaman_pdf'];
const IMPORT_GURU_=['guru_id','nama_guru','halaman_pdf','jumlah_waktu_pdf','jumlah_waktu_ekstrak','beza','bil_blok_pdf','status_semakan','aktif'];
const IMPORT_WAKTU_=['susunan_pdf','label_waktu','masa_mula','masa_tamat','jenis'];

function reliefPage_(e){
  requireAdmin_();const isImport=e&&e.parameter&&e.parameter.page==='import';
  const url=ScriptApp.getService().getUrl()||'';
  let html=HtmlService.createHtmlOutputFromFile(isImport?'ImportPanel':'Index').getContent();
  if(isImport){html=html.replace('<!--APP_URL-->',htmlEscape_(url));}
  else {
    const link='<a href="'+htmlEscape_(url+'?page=import')+'" target="_top" class="screen-only" style="display:inline-block;background:white;border:1px solid #cbd8dd;border-radius:8px;padding:9px 14px;color:#183342;text-decoration:none;font-weight:600">Import jadual</a>';
    if(html.indexOf('<div class="actions">')>=0)html=html.replace('<div class="actions">','<div class="actions">'+link);
    else html=html.replace('<body>','<body><nav class="screen-only" style="padding:12px">'+link+'</nav>');
    // Sesuaikan label sumber cetakan apabila pengguna melihat tarikh sebelum import.
    const hook='<script>if(typeof render==="function"&&typeof state!=="undefined"){const renderV10=render;render=function(){if(state.day&&state.boot&&state.day.sourceLabel)state.boot.source=state.day.sourceLabel;renderV10();if(state.day&&state.day.sourceLabel&&document.getElementById("source"))document.getElementById("source").textContent="Jadual sumber: "+state.day.sourceLabel;const select=document.getElementById("absTeacher");if(select&&state.day&&state.day.teachers){const previous=select.value;select.replaceChildren();const empty=document.createElement("option");empty.value="";empty.textContent="Pilih guru";select.appendChild(empty);state.day.teachers.forEach(function(t){const option=document.createElement("option");option.value=t.id;option.textContent=t.name;select.appendChild(option);});select.value=previous;}};}<\/script>';
    html=html.replace('</body>',hook+'</body>');
  }
  return HtmlService.createHtmlOutput(html).setTitle(isImport?'Import Jadual — Sistem Relief':'Sistem Relief Sekolah').addMetaTag('viewport','width=device-width, initial-scale=1');
}
function getImportInfo(){
  requireAdmin_();const ss=database_(),journal=importJournal_();
  if(journal)return {recovery:true,message:'Import '+journal.id+' belum selesai. Pulihkan atau lengkapkan transaksi sebelum menggunakan app.',today:today_()};
  const c=loadContext_();return {recovery:false,today:today_(),school:c.settings.NAMA_SEKOLAH||'Sekolah',source:c.settings.JADUAL_SUMBER||'',
    teachers:Object.values(c.byTeacher).sort((a,b)=>a.name.localeCompare(b.name)),revision:importRevision_(ss),
    history:importLogs_(ss).slice(-10).reverse().map(r=>({id:r.import_id,date:r.kuat_kuasa,label:r.label,status:r.status}))};
}
function previewTimetable(request){requireAdmin_();assertImportIdle_();const plan=buildImportPlan_(request);return importPreview_(plan);}
function commitTimetable(request){
  requireAdmin_();const lock=LockService.getScriptLock();lock.waitLock(30000);
  let journal=null,stage='Semak data import';
  try {
    assertImportIdle_();
    const plan=buildImportPlan_(request);
    if(!request.confirmed||request.signature!==plan.signature)throw Error('Pratonton telah berubah. Semak semula fail dan klik Semak import dahulu.');
    const ss=plan.ss,id='I-'+Utilities.getUuid(),stamp=id.slice(-12).replace(/-/g,'');
    const backups={};
    stage='Cipta sandaran';
    ['Jadual','Guru','Waktu','Ketidakhadiran','Relief','Tetapan'].forEach(name=>{
      const s=ss.getSheetByName(name);if(!s)throw Error('Tab '+name+' tiada. Import dihentikan sebelum overwrite.');
      backups[name]='B_'+stamp+'_'+name;s.copyTo(ss).setName(backups[name]).hideSheet();
    });
    SpreadsheetApp.flush();
    journal={id:id,backups:backups,label:plan.label,date:plan.date};
    PropertiesService.getScriptProperties().setProperty('IMPORT_JOURNAL',JSON.stringify(journal));
    stage='Rekod LogImport';writeLog_(ss,journal,'BERJALAN',plan);
    stage='Ganti tab Guru';
    overwriteTable_(ss,'Guru',IMPORT_GURU_,plan.teacherRows);
    stage='Ganti tab Jadual';
    overwriteTable_(ss,'Jadual',IMPORT_JADUAL_,plan.lessonRows);
    stage='Ganti tab Waktu';
    overwriteTable_(ss,'Waktu',IMPORT_WAKTU_,plan.timeRows);
    stage='Kemas kini rekod relief';
    const now=timestamp_();
    plan.cancelled.forEach(item=>{const r=plan.context.reliefs.find(r=>r.relief_id===item.id);patch_(ss,'Relief',r,{status:'BATAL',dikemas_kini_pada:now});});
    stage='Kemas kini Tetapan';setSetting_(ss,'JADUAL_SUMBER',plan.label+' — mulai '+plan.date);
    setSetting_(ss,'VERSI_APP','1.1.1');
    SpreadsheetApp.flush();
    stage='Sahkan data selepas import';const check=validateSource_(ss);
    if(check.lessons.length!==plan.lessonRows.length||check.teachers.length!==plan.activeCount)throw Error('Semakan selepas simpan tidak sepadan.');
    stage='Lengkapkan LogImport';writeLog_(ss,journal,'BERJAYA',plan);SpreadsheetApp.flush();
    PropertiesService.getScriptProperties().deleteProperty('IMPORT_JOURNAL');
    return {ok:true,id:id,message:'Import berjaya. Jadual semasa telah diganti.',teachers:plan.activeCount,lessons:plan.lessonRows.length,cancelled:plan.cancelled.length,retained:plan.retained,backups:backups};
  } catch(error) {
    const detail=stage+': '+error.message;
    if(journal){
      try {restoreImport_(journal);throw Error('Import gagal; semua data telah dipulihkan daripada sandaran. '+detail);}
      catch(recoveryError){
        if(!importJournal_())throw recoveryError;
        throw Error('Import tidak selesai. Data dikunci untuk pemulihan. Buka Import jadual dan klik Pulihkan import. '+detail);
      }
    }
    throw error;
  } finally {lock.releaseLock();}
}
function recoverTimetableImport(){
  requireAdmin_();const lock=LockService.getScriptLock();lock.waitLock(30000);
  try {
    const j=importJournal_();if(!j)return {ok:true,message:'Tiada transaksi tertangguh.'};
    const completed=importLogs_(database_()).find(r=>r.import_id===j.id&&r.status==='BERJAYA');
    if(completed){PropertiesService.getScriptProperties().deleteProperty('IMPORT_JOURNAL');return {ok:true,message:'Import sudah berjaya. Kunci transaksi telah dilepaskan.'};}
    restoreImport_(j);return {ok:true,message:'Data sebelum import telah dipulihkan. Sandaran dan log dikekalkan.'};
  }finally{lock.releaseLock();}
}

function buildImportPlan_(request){
  if(!request||JSON.stringify(request).length>8000000)throw Error('Permintaan import kosong atau terlalu besar (maksimum 8 MB data teks).');
  const ss=database_(),revision=importRevision_(ss);
  if(request.revision!==revision)throw Error('Data telah berubah sejak halaman import dibuka. Muat semula halaman import.');
  const date=validateDate_(request.effectiveDate),label=cleanText_(request.label,150);
  if(!label)throw Error('Isi nama atau edisi jadual.');
  if(date<today_())throw Error('Tarikh kuat kuasa import mesti hari ini atau selepasnya. Rekod tarikh lama dikekalkan.');
  const success=importLogs_(ss).filter(r=>r.status==='BERJAYA');
  if(success.length&&date<success[success.length-1].kuat_kuasa)throw Error('Tarikh kuat kuasa tidak boleh mendahului import berjaya yang terakhir.');
  if(!Array.isArray(request.teachers)||!request.teachers.length||request.teachers.length>500)throw Error('Fail mesti mengandungi 1 hingga 500 guru.');
  if(!Array.isArray(request.rows)||!request.rows.length||request.rows.length>20000)throw Error('Fail mesti mengandungi 1 hingga 20,000 waktu pengajaran.');
  const c=loadContext_(),registry=Object.values(c.byTeacher),sourceTeachers=new Map(),nameSeen=new Set(),targetSeen=new Set(),mapped=new Map();
  let next=Math.max(0,...registry.map(t=>/^G\d+$/.test(t.id)?Number(t.id.slice(1)):0))+1;
  const exactNames=new Map();registry.forEach(t=>{const k=teacherNameKey_(t.name);if(!exactNames.has(k))exactNames.set(k,[]);exactNames.get(k).push(t.id);});
  const added=[],matched=[],mappings=request.mapping||{};
  request.teachers.forEach(t=>{
    const sid=String(t.sourceId||''),name=cleanText_(t.name,150),key=teacherNameKey_(name);
    if(!/^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(sid)||!name||sourceTeachers.has(sid)||nameSeen.has(key))throw Error('ID sumber atau nama guru kosong/berganda: '+sid+' '+name);
    sourceTeachers.set(sid,{sourceId:sid,name:name});nameSeen.add(key);
    const exact=exactNames.get(key)||[];
    let target=Object.prototype.hasOwnProperty.call(mappings,sid)?String(mappings[sid]):exact.length===1?exact[0]:'';
    if(!target)throw Error('Padankan guru '+name+' dengan daftar sedia ada atau pilih Guru baharu.');
    if(target==='NEW'){
      do{target='G'+String(next++).padStart(3,'0');}while(c.byTeacher[target]);
      added.push({id:target,name:name});
    }else if(!c.byTeacher[target])throw Error('Padanan guru tidak sah: '+name);
    else matched.push({id:target,name:name,previous:c.byTeacher[target].name});
    if(targetSeen.has(target))throw Error('Dua guru sumber dipadankan kepada ID yang sama. Semak padanan '+name+'.');
    targetSeen.add(target);mapped.set(sid,target);
  });
  const days=['','Isnin','Selasa','Rabu','Khamis','Jumaat'],slotSeen=new Set(),timeMap=new Map(),lessonRows=[];
  request.rows.forEach((r,i)=>{
    const sid=String(r.guru_id||''),t=sourceTeachers.get(sid),gid=mapped.get(sid),day=Number(r.hari_no),period=Number(r.waktu);
    if(!t||!gid||!Number.isInteger(day)||day<1||day>5||!Number.isInteger(period)||period<1||period>30)throw Error('Guru, hari_no atau waktu tidak sah pada baris data '+(i+1)+'.');
    if(r.nama_guru&&teacherNameKey_(String(r.nama_guru))!==teacherNameKey_(t.name))throw Error('Nama guru dan guru_id tidak sepadan pada baris '+(i+1)+'.');
    if(r.hari&&String(r.hari).trim().toLowerCase()!==days[day].toLowerCase())throw Error('hari dan hari_no tidak sepadan pada baris '+(i+1)+'.');
    const start=minute_(r.masa_mula),end=minute_(r.masa_tamat);
    if(start>=end||end-start>180)throw Error('Julat masa tidak sah pada baris '+(i+1)+'.');
    const subject=cleanText_(r.subjek_label,250),classLabel=cleanText_(r.kelas_label,500),room=cleanText_(r.bilik_label,150);
    if(!subject||!classLabel)throw Error('Subjek dan kelas wajib diisi pada baris '+(i+1)+'.');
    const id=gid+'-H'+day+'-W'+String(period).padStart(2,'0');
    if(slotSeen.has(id))throw Error('Waktu guru berganda: '+t.name+', '+days[day]+', waktu '+period+'.');slotSeen.add(id);
    if(timeMap.has(period)&&(timeMap.get(period).start!==start||timeMap.get(period).end!==end))throw Error('Nombor waktu '+period+' mempunyai masa berlainan. Gunakan nombor waktu unik untuk slot masa yang berlainan.');
    timeMap.set(period,{start:start,end:end});
    lessonRows.push([id,gid,t.name,day,days[day],period,clock_(start),clock_(end),subject,classLabel,room,
      cleanText_(String(r.blok_id||id),120),cleanText_(String(r.halaman_pdf||''),30)]);
  });
  lessonRows.sort((a,b)=>a[1].localeCompare(b[1])||a[3]-b[3]||minute_(a[6])-minute_(b[6]));
  const byTeacherDay=new Map();lessonRows.forEach(r=>{const k=r[1]+'|'+r[3];if(!byTeacherDay.has(k))byTeacherDay.set(k,[]);byTeacherDay.get(k).push(r);});
  byTeacherDay.forEach(rows=>{for(let i=1;i<rows.length;i++)if(minute_(rows[i][6])<minute_(rows[i-1][7]))throw Error('Masa pengajaran bertindih untuk '+rows[i][2]+' pada '+rows[i][4]+'.');});
  const nameById=new Map();request.teachers.forEach(t=>nameById.set(mapped.get(String(t.sourceId)),cleanText_(t.name,150)));
  const allTeachers=registry.map(t=>({id:t.id,name:nameById.get(t.id)||t.name,active:targetSeen.has(t.id)})).concat(added.map(t=>({id:t.id,name:t.name,active:true})));
  const teacherRows=allTeachers.sort((a,b)=>a.id.localeCompare(b.id)).map(t=>{const count=lessonRows.filter(r=>r[1]===t.id).length;return [t.id,t.name,'','',count,'','','DISEMAK_IMPORT',t.active?'YA':'TIDAK'];});
  const newSource=sourceFromMatrices_(teacherRows,lessonRows);
  const changes=diffLessons_(c,newSource),cancelled=[],keep=[];
  c.reliefs.filter(r=>r.status==='AKTIF'&&r.tarikh>=date).forEach(r=>{
    const old=c.byLesson[r.jadual_id],l=newSource.byLesson[r.jadual_id];let reason='';
    if(!old||!l||lessonKey_(old)!==lessonKey_(l))reason='Kelas, subjek, bilik atau masa berubah / tiada dalam jadual baharu.';
    else if(r.guru_asal_id!==l.teacherId||l.day!==weekday_(r.tarikh))reason='Rujukan kelas tidak lagi sepadan.';
    else if(!newSource.byTeacher[r.guru_ganti_id]||!newSource.byTeacher[r.guru_ganti_id].active)reason='Guru ganti tidak aktif dalam jadual baharu.';
    else if(!isAbsent_(c,r.tarikh,l.teacherId,l.start,l.end))reason='Guru asal tidak lagi mempunyai ketidakhadiran yang sepadan.';
    if(reason)cancelled.push({id:r.relief_id,date:r.tarikh,jadualId:r.jadual_id,reason:reason});else keep.push(r);
  });
  const prospective=Object.assign({},c,newSource,{reliefs:keep});
  const validKeep=[];
  keep.forEach(r=>{const reasons=candidateReasons_(prospective,r.tarikh,newSource.byLesson[r.jadual_id],r.guru_ganti_id,r.relief_id);if(reasons.length)cancelled.push({id:r.relief_id,date:r.tarikh,jadualId:r.jadual_id,reason:reasons.join('; ')});else validKeep.push(r);});
  const timeRows=Array.from(timeMap).sort((a,b)=>a[0]-b[0]).map(([p,t],i)=>[i+1,String(p),clock_(t.start),clock_(t.end),'PENGAJARAN']);
  const inactive=allTeachers.filter(t=>!t.active).map(t=>({id:t.id,name:t.name}));
  const summary={teachers:targetSeen.size,lessons:lessonRows.length,matched:matched.length,newTeachers:added.length,inactive:inactive.length,changed:changes.changed,added:changes.added,removed:changes.removed,cancelled:cancelled.length,retained:validKeep.length};
  const signature=digest_(JSON.stringify({revision:revision,date:date,label:label,teacherRows:teacherRows,lessonRows:lessonRows,cancelled:cancelled}));
  return {ss:ss,context:c,date:date,label:label,revision:revision,signature:signature,teacherRows:teacherRows,lessonRows:lessonRows,timeRows:timeRows,activeCount:targetSeen.size,added:added,matched:matched,inactive:inactive,cancelled:cancelled,retained:validKeep.length,summary:summary};
}
function importPreview_(p){return {signature:p.signature,revision:p.revision,date:p.date,label:p.label,summary:p.summary,newTeachers:p.added,inactive:p.inactive,cancelled:p.cancelled,sample:p.lessonRows.slice(0,15).map(r=>({name:r[2],day:r[4],period:r[5],start:r[6],end:r[7],subject:r[8],classLabel:r[9]}))};}
function sourceFromMatrices_(teachers,lessons){
  const byTeacher={},byLesson={};teachers.forEach(r=>byTeacher[r[0]]={id:r[0],name:r[1],active:r[8]==='YA'});
  const normalized=lessons.map(r=>{const l={id:r[0],teacherId:r[1],day:r[3],period:r[5],start:minute_(r[6]),end:minute_(r[7]),subject:r[8],classLabel:r[9],room:r[10],blockId:r[11],page:r[12]};byLesson[l.id]=l;return l;});
  return {lessons:normalized,byLesson:byLesson,byTeacher:byTeacher,teachers:Object.values(byTeacher).filter(t=>t.active)};
}
function lessonKey_(l){return JSON.stringify([l.teacherId,l.day,l.period,l.start,l.end,l.subject,l.classLabel,l.room]);}
function diffLessons_(old,next){let added=0,removed=0,changed=0;next.lessons.forEach(l=>{if(!old.byLesson[l.id])added++;else if(lessonKey_(l)!==lessonKey_(old.byLesson[l.id]))changed++;});old.lessons.forEach(l=>{if(!next.byLesson[l.id])removed++;});return {added:added,removed:removed,changed:changed};}
function teacherNameKey_(s){return String(s).normalize('NFKC').trim().replace(/\s+/g,' ').toUpperCase();}
function sourceForDate_(ss,date){
  if(!date)return ss;
  const entry=importLogs_(ss).find(r=>r.status==='BERJAYA'&&date<r.kuat_kuasa);
  if(!entry)return ss;
  let names;try{names=JSON.parse(entry.sandaran_json);}catch(e){throw Error('Log sandaran jadual rosak. Semak LogImport.');}
  return {getSheetByName:function(n){const s=ss.getSheetByName(names[n]||n);if(!s)throw Error('Sandaran jadual hilang: '+n+'.');return s;}};
}
function importLogs_(ss){return ss.getSheetByName('LogImport')?readRows_(ss,'LogImport',IMPORT_LOG_):[];}
function importRevision_(ss){return digest_(JSON.stringify(['Jadual','Guru','Waktu','Ketidakhadiran','Relief','Tetapan','LogImport'].map(n=>{const s=ss.getSheetByName(n);return [n,s?s.getDataRange().getDisplayValues():[]];})));}
function importJournal_(){const raw=PropertiesService.getScriptProperties().getProperty('IMPORT_JOURNAL');if(!raw)return null;try{return JSON.parse(raw);}catch(e){throw Error('Jurnal import rosak. Jangan ubah data sebelum memulihkan sandaran.');}}
function assertImportIdle_(){if(importJournal_())throw Error('Import belum selesai. Buka Import jadual dan klik Pulihkan import sebelum menggunakan app.');}
function overwriteTable_(ss,name,heads,rows){const s=ss.getSheetByName(name)||ss.insertSheet(name);const data=[heads].concat(rows).map(r=>r.map(safeCell_));plainTextColumns_(s,1,1,data.length,heads.length);s.clearContents();s.getRange(1,1,data.length,heads.length).setValues(data);s.getRange(1,1,1,heads.length).setBackground('#183d51').setFontColor('#fff').setFontWeight('bold');s.setFrozenRows(1);}
function setSetting_(ss,key,value){const rows=readRows_(ss,'Tetapan',RELIEF_SCHEMA_.Tetapan),r=rows.find(r=>r.kunci===key);if(r)patch_(ss,'Tetapan',r,{nilai:value});else append_(ss,'Tetapan',[key,value]);}
function writeLog_(ss,j,status,plan){
  const s=ensureTable_(ss,'LogImport',IMPORT_LOG_),existing=importLogs_(ss).find(r=>r.import_id===j.id);
  const values=[j.id,timestamp_(),j.date,j.label,status,JSON.stringify(j.backups),JSON.stringify(plan?plan.cancelled:[]),JSON.stringify(plan?plan.summary:{})];
  const heads=assertHeaders_(s,IMPORT_LOG_),row=existing?existing._row:s.getLastRow()+1;plainTextColumns_(s,row,1,1,heads.length);s.getRange(row,1,1,heads.length).setValues([heads.map(h=>{const i=IMPORT_LOG_.indexOf(h);return i<0?'':safeCell_(values[i]);})]);
}
function restoreImport_(j){
  const ss=database_();
  // Semak semua sandaran dahulu. Jangan pulihkan sebahagian jika sandaran tidak lengkap.
  Object.keys(j.backups).forEach(n=>{if(!ss.getSheetByName(j.backups[n]))throw Error('Sandaran '+n+' tidak ditemui.');});
  Object.keys(j.backups).forEach(n=>{const src=ss.getSheetByName(j.backups[n]),dst=ss.getSheetByName(n)||ss.insertSheet(n);dst.clearContents();src.getDataRange().copyTo(dst.getRange(1,1,src.getLastRow(),src.getLastColumn()));});
  SpreadsheetApp.flush();validateSource_(ss);writeLog_(ss,j,'DIPULIHKAN',null);SpreadsheetApp.flush();PropertiesService.getScriptProperties().deleteProperty('IMPORT_JOURNAL');
}
function htmlEscape_(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
