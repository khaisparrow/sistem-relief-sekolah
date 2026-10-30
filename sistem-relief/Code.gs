/** Sistem Relief Sekolah 1.1.1. Kekalkan fail Index.html versi sedia ada. */
const RELIEF_TZ_ = 'Asia/Kuala_Lumpur';
const RELIEF_SCHEMA_ = {
  Tetapan: ['kunci','nilai'],
  Ketidakhadiran: ['ketidakhadiran_id','tarikh','guru_id','masa_mula','masa_tamat','sebab','status','dicipta_pada','dikemas_kini_pada'],
  Relief: ['relief_id','tarikh','jadual_id','guru_asal_id','guru_ganti_id','catatan','status','dicipta_pada','dikemas_kini_pada']
};
function setupSistem() {
  const ss=SpreadsheetApp.getActiveSpreadsheet();
  if(!ss)throw Error('Buka Extensions > Apps Script daripada spreadsheet jadual, kemudian jalankan setupSistem.');
  const email=String(Session.getActiveUser().getEmail()||'').toLowerCase();
  const effective=String(Session.getEffectiveUser().getEmail()||'').toLowerCase();
  if(!email||email!==effective)throw Error('Jalankan pemasangan menggunakan akaun pemilik projek.');
  const props=PropertiesService.getScriptProperties(),old=props.getProperty('ADMIN_EMAIL');
  if(old&&old!==email)throw Error('Hanya pentadbir asal boleh menjalankan pemasangan semula.');
  const lock=LockService.getScriptLock();lock.waitLock(20000);
  try {
    validateSource_(ss);
    Object.keys(RELIEF_SCHEMA_).forEach(n=>{const s=ss.getSheetByName(n);if(s&&s.getLastRow())assertHeaders_(s,RELIEF_SCHEMA_[n]);});
    ss.setSpreadsheetTimeZone(RELIEF_TZ_);
    Object.keys(RELIEF_SCHEMA_).forEach(n=>ensureTable_(ss,n,RELIEF_SCHEMA_[n]));
    const settings=readRows_(ss,'Tetapan',RELIEF_SCHEMA_.Tetapan);
    const defaults={NAMA_SEKOLAH:'SMK TAMAN DESA 2',JADUAL_SUMBER:'Jilid 5 — terjana 19/6/2026',ZON_MASA:RELIEF_TZ_,VERSI_APP:'1.1.1'};
    Object.keys(defaults).forEach(k=>{if(!settings.some(r=>r.kunci===k))append_(ss,'Tetapan',[k,defaults[k]]);});
    props.setProperties({SPREADSHEET_ID:ss.getId(),ADMIN_EMAIL:email});
    SpreadsheetApp.flush();
    const msg='Pemasangan berjaya. Data asal dikekalkan. '+validateSource_(ss).teachers.length+' guru ditemui.';
    console.log(msg);return msg;
  }finally{lock.releaseLock();}
}
function doGet(e){return reliefPage_(e);}
function requireAdmin_(){
  const expected=PropertiesService.getScriptProperties().getProperty('ADMIN_EMAIL');
  const actual=String(Session.getActiveUser().getEmail()||'').toLowerCase();
  if(!expected)throw Error('Sistem belum dipasang. Jalankan setupSistem dari editor Apps Script.');
  if(!actual||actual!==expected)throw Error('Akses terhad kepada penyelaras yang memasang sistem. Gunakan Gmail yang sama dan deployment Only myself.');
}
function getBootstrap(){
  requireAdmin_();const c=loadContext_();
  return {school:c.settings.NAMA_SEKOLAH||'Sekolah',source:c.settings.JADUAL_SUMBER||'',today:today_(),teachers:c.teachers,version:'1.1.1',admin:PropertiesService.getScriptProperties().getProperty('ADMIN_EMAIL')};
}
function getDay(date){requireAdmin_();validateDate_(date);return dayView_(loadContext_(date),date);}
function getCandidates(request){
  requireAdmin_();const date=validateDate_(request&&request.date),c=loadContext_(date),task=findTask_(c,date,request.jadualId);
  const candidates=c.teachers.map(t=>({id:t.id,name:t.name,reasons:candidateReasons_(c,date,task.lesson,t.id,task.assignment?task.assignment.relief_id:''),reliefCount:c.reliefs.filter(r=>r.tarikh===date&&r.status==='AKTIF'&&r.guru_ganti_id===t.id).length}))
    .sort((a,b)=>(a.reasons.length>0)-(b.reasons.length>0)||a.reliefCount-b.reliefCount||a.name.localeCompare(b.name));
  return {revision:revision_(c,date),candidates:candidates};
}
function saveAbsence(request){return mutate_(request,(c,date)=>{
  const t=teacher_(c,request.teacherId),start=minute_(request.start),end=minute_(request.end);
  if(t.active===false)throw Error('Guru ini tidak aktif dalam jadual pada tarikh dipilih.');
  if(start>=end)throw Error('Masa tamat mesti selepas masa mula.');
  if(c.absences.some(a=>a.status==='AKTIF'&&a.tarikh===date&&a.guru_id===t.id))throw Error('Guru ini sudah mempunyai rekod ketidakhadiran pada tarikh tersebut. Batalkan rekod lama untuk menukar tempoh.');
  const clashes=c.reliefs.filter(r=>{const l=c.byLesson[r.jadual_id];return r.status==='AKTIF'&&r.tarikh===date&&r.guru_ganti_id===t.id&&l&&overlaps_(start,end,l.start,l.end);});
  if(clashes.length)throw Error('Guru ini sudah ditetapkan untuk '+clashes.length+' waktu relief. Tukar atau batalkan penetapan dahulu.');
  const now=timestamp_();append_(c.ss,'Ketidakhadiran',['A-'+Utilities.getUuid(),date,t.id,clock_(start),clock_(end),cleanText_(request.reason,300),'AKTIF',now,now]);
});}
function cancelAbsence(request){return mutate_(request,(c,date)=>{
  const a=c.absences.find(r=>r.ketidakhadiran_id===request.absenceId&&r.tarikh===date&&r.status==='AKTIF');
  if(!a)throw Error('Rekod ketidakhadiran tidak ditemui atau telah dibatalkan.');
  const now=timestamp_();
  c.reliefs.filter(r=>r.tarikh===date&&r.guru_asal_id===a.guru_id&&r.status==='AKTIF').forEach(r=>patch_(c.ss,'Relief',r,{status:'BATAL',dikemas_kini_pada:now}));
  patch_(c.ss,'Ketidakhadiran',a,{status:'BATAL',dikemas_kini_pada:now});
});}
function saveAssignment(request){return mutate_(request,(c,date)=>{
  const task=findTask_(c,date,request.jadualId),t=teacher_(c,request.teacherId);
  const reasons=candidateReasons_(c,date,task.lesson,t.id,task.assignment?task.assignment.relief_id:'');
  if(reasons.length)throw Error('Guru tidak boleh ditetapkan: '+reasons.join('; '));
  const now=timestamp_(),note=cleanText_(request.note,500);
  if(task.assignment)patch_(c.ss,'Relief',task.assignment,{guru_ganti_id:t.id,catatan:note,dikemas_kini_pada:now});
  else append_(c.ss,'Relief',['R-'+Utilities.getUuid(),date,task.lesson.id,task.lesson.teacherId,t.id,note,'AKTIF',now,now]);
});}
function cancelAssignment(request){return mutate_(request,(c,date)=>{
  const r=c.reliefs.find(r=>r.relief_id===request.reliefId&&r.tarikh===date&&r.status==='AKTIF');
  if(!r)throw Error('Penetapan tidak ditemui atau telah dibatalkan.');
  patch_(c.ss,'Relief',r,{status:'BATAL',dikemas_kini_pada:timestamp_()});
});}
function mutate_(request,callback){
  requireAdmin_();const date=validateDate_(request&&request.date),lock=LockService.getScriptLock();lock.waitLock(20000);
  try{const c=loadContext_(date);if(!request.revision||request.revision!==revision_(c,date))throw Error('Data telah berubah. Klik Muat semula sebelum menyimpan sekali lagi.');callback(c,date);SpreadsheetApp.flush();return dayView_(loadContext_(date),date);}finally{lock.releaseLock();}
}
function loadContext_(date){
  const ss=database_();assertImportIdle_();const sourceContainer=sourceForDate_(ss,date),source=validateSource_(sourceContainer);
  const settings={};readRows_(sourceContainer,'Tetapan',RELIEF_SCHEMA_.Tetapan).forEach(r=>settings[r.kunci]=r.nilai);
  const c={ss:ss,settings:settings,teachers:source.teachers,byTeacher:source.byTeacher,lessons:source.lessons,byLesson:source.byLesson,
    absences:readRows_(ss,'Ketidakhadiran',RELIEF_SCHEMA_.Ketidakhadiran).filter(r=>!date||r.tarikh===date),
    reliefs:readRows_(ss,'Relief',RELIEF_SCHEMA_.Relief).filter(r=>!date||r.tarikh===date)};
  const seenA={},seenR={};
  c.absences.forEach(a=>{validateDate_(a.tarikh);teacher_(c,a.guru_id);if(minute_(a.masa_mula)>=minute_(a.masa_tamat)||!['AKTIF','BATAL'].includes(a.status))throw Error('Rekod Ketidakhadiran tidak sah pada baris '+a._row+'.');if(a.status==='AKTIF'){const k=a.tarikh+'|'+a.guru_id;if(seenA[k])throw Error('Rekod ketidakhadiran aktif berganda.');seenA[k]=true;}});
  c.reliefs.forEach(r=>{validateDate_(r.tarikh);if(!['AKTIF','BATAL'].includes(r.status))throw Error('Status Relief tidak sah pada baris '+r._row+'.');if(r.status==='AKTIF'){const k=r.tarikh+'|'+r.jadual_id;if(seenR[k])throw Error('Penetapan relief aktif berganda.');seenR[k]=true;}});
  return c;
}
function validateSource_(ss){
  const rawTeachers=readRows_(ss,'Guru',['guru_id','nama_guru']);if(!rawTeachers.length)throw Error('Tab Guru tiada data.');
  const byTeacher={};rawTeachers.forEach(t=>{if(!t.guru_id||!t.nama_guru||byTeacher[t.guru_id])throw Error('ID atau nama guru kosong/berganda pada tab Guru.');byTeacher[t.guru_id]={id:t.guru_id,name:t.nama_guru,active:!['TIDAK','FALSE','0'].includes(String(t.aktif||'YA').toUpperCase())};});
  const raw=readRows_(ss,'Jadual',['jadual_id','guru_id','hari_no','hari','waktu','masa_mula','masa_tamat','subjek_label','kelas_label','bilik_label','blok_id','halaman_pdf']);
  if(!raw.length)throw Error('Tab Jadual tiada data.');const byLesson={},slots={},byTeacherDay={};
  const lessons=raw.map(r=>{
    const day=Number(r.hari_no),period=Number(r.waktu);
    if(!r.jadual_id||byLesson[r.jadual_id]||!byTeacher[r.guru_id]||!byTeacher[r.guru_id].active||!Number.isInteger(day)||day<1||day>5||!Number.isInteger(period)||period<1||period>30)throw Error('Data Jadual tidak sah pada baris '+r._row+'.');
    const start=minute_(r.masa_mula),end=minute_(r.masa_tamat);if(start>=end||!r.subjek_label||!r.kelas_label)throw Error('Masa, subjek atau kelas tidak sah pada Jadual.');
    const k=r.guru_id+'|'+day+'|'+period;if(slots[k])throw Error('Waktu guru berganda pada tab Jadual.');slots[k]=true;
    const l={id:r.jadual_id,teacherId:r.guru_id,day:day,period:period,start:start,end:end,subject:r.subjek_label,classLabel:r.kelas_label,room:r.bilik_label||'',blockId:r.blok_id||'',page:r.halaman_pdf||''};byLesson[l.id]=l;
    const tk=r.guru_id+'|'+day;if(!byTeacherDay[tk])byTeacherDay[tk]=[];byTeacherDay[tk].push(l);return l;
  });
  Object.keys(byTeacherDay).forEach(k=>{const a=byTeacherDay[k].sort((a,b)=>a.start-b.start);for(let i=1;i<a.length;i++)if(a[i].start<a[i-1].end)throw Error('Masa pengajaran guru bertindih: '+a[i].id);});
  return {teachers:Object.values(byTeacher).filter(t=>t.active).sort((a,b)=>a.name.localeCompare(b.name)),byTeacher:byTeacher,lessons:lessons,byLesson:byLesson};
}
function dayView_(c,date){
  const day=weekday_(date),absences=c.absences.filter(a=>a.tarikh===date&&a.status==='AKTIF');
  const tasks=c.lessons.filter(l=>l.day===day&&isAbsent_(c,date,l.teacherId,l.start,l.end)).map(l=>{
    const r=c.reliefs.find(r=>r.tarikh===date&&r.jadual_id===l.id&&r.status==='AKTIF');
    const warnings=r?candidateReasons_(c,date,l,r.guru_ganti_id,r.relief_id):[];
    if(r&&r.guru_asal_id!==l.teacherId)warnings.push('ID guru asal tidak sepadan dengan Jadual.');
    return {id:l.id,originalId:l.teacherId,original:teacher_(c,l.teacherId).name,period:l.period,start:clock_(l.start),end:clock_(l.end),subject:l.subject,classLabel:l.classLabel,room:l.room,page:l.page,
      reliefId:r?r.relief_id:'',substituteId:r?r.guru_ganti_id:'',substitute:r&&c.byTeacher[r.guru_ganti_id]?c.byTeacher[r.guru_ganti_id].name:'',note:r?r.catatan:'',warnings:warnings,status:warnings.length?'SEMAK':r?'DITETAPKAN':'BELUM DITETAPKAN'};
  }).sort((a,b)=>minute_(a.start)-minute_(b.start)||a.original.localeCompare(b.original));
  const ids={};tasks.forEach(t=>ids[t.id]=true);
  const orphaned=c.reliefs.filter(r=>r.tarikh===date&&r.status==='AKTIF'&&!ids[r.jadual_id]).map(r=>({id:r.relief_id,jadualId:r.jadual_id,substitute:c.byTeacher[r.guru_ganti_id]?c.byTeacher[r.guru_ganti_id].name:r.guru_ganti_id}));
  const workloads=c.teachers.map(t=>({id:t.id,name:t.name,teaching:c.lessons.filter(l=>l.day===day&&l.teacherId===t.id).length,relief:c.reliefs.filter(r=>r.tarikh===date&&r.status==='AKTIF'&&r.guru_ganti_id===t.id).length,absent:absences.some(a=>a.guru_id===t.id)})).sort((a,b)=>b.relief-a.relief||a.name.localeCompare(b.name));
  return {date:date,teachers:c.teachers,sourceLabel:c.settings.JADUAL_SUMBER||'',day:['Ahad','Isnin','Selasa','Rabu','Khamis','Jumaat','Sabtu'][day],revision:revision_(c,date),
    absences:absences.map(a=>({id:a.ketidakhadiran_id,teacherId:a.guru_id,name:teacher_(c,a.guru_id).name,start:a.masa_mula,end:a.masa_tamat,reason:a.sebab})),tasks:tasks,orphaned:orphaned,workloads:workloads,
    stats:{absent:absences.length,total:tasks.length,assigned:tasks.filter(t=>t.status==='DITETAPKAN').length,pending:tasks.filter(t=>t.status==='BELUM DITETAPKAN').length,warnings:tasks.filter(t=>t.status==='SEMAK').length+orphaned.length}};
}
function findTask_(c,date,id){const l=c.byLesson[String(id||'')];if(!l||l.day!==weekday_(date)||!isAbsent_(c,date,l.teacherId,l.start,l.end))throw Error('Waktu ini tidak memerlukan relief pada tarikh tersebut. Muat semula.');return {lesson:l,assignment:c.reliefs.find(r=>r.tarikh===date&&r.jadual_id===l.id&&r.status==='AKTIF')||null};}
function candidateReasons_(c,date,l,id,excluded){
  const reasons=[];if(!c.byTeacher[id])return ['Guru tidak ditemui dalam daftar Guru.'];
  if(c.byTeacher[id].active===false)reasons.push('Guru tidak aktif dalam jadual ini.');
  if(id===l.teacherId)reasons.push('Guru asal bagi kelas ini.');
  if(isAbsent_(c,date,id,l.start,l.end))reasons.push('Tidak hadir dalam tempoh ini.');
  if(c.lessons.some(o=>o.teacherId===id&&o.day===weekday_(date)&&overlaps_(l.start,l.end,o.start,o.end)))reasons.push('Bertindih dengan kelas asal.');
  if(c.reliefs.some(r=>{if(r.status!=='AKTIF'||r.tarikh!==date||r.guru_ganti_id!==id||r.relief_id===excluded)return false;const o=c.byLesson[r.jadual_id];return !o||overlaps_(l.start,l.end,o.start,o.end);}))reasons.push('Bertindih dengan relief lain atau rekod relief perlu disemak.');return reasons;
}
function isAbsent_(c,date,id,start,end){return c.absences.some(a=>a.status==='AKTIF'&&a.tarikh===date&&a.guru_id===id&&overlaps_(start,end,minute_(a.masa_mula),minute_(a.masa_tamat)));}
function teacher_(c,id){if(!c.byTeacher[id])throw Error('Guru tidak ditemui. Muat semula data.');return c.byTeacher[id];}
function overlaps_(a,b,c,d){return a<d&&c<b;}
function clock_(m){return ('0'+Math.floor(m/60)).slice(-2)+':'+('0'+m%60).slice(-2);}
function minute_(value){const s=String(value==null?'':value).trim(),m=/^(\d{1,2}):(\d{2})(?::00)?$/.exec(s);if(!m||+m[1]>23||+m[2]>59)throw Error('Masa tidak sah: '+s+'. Gunakan HH:mm, contohnya 09:30.');return +m[1]*60+(+m[2]);}
function validateDate_(date){if(typeof date!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(date))throw Error('Tarikh mesti dalam format YYYY-MM-DD.');const d=new Date(date+'T12:00:00Z');if(isNaN(d.getTime())||d.toISOString().slice(0,10)!==date||date<'2000-01-01'||date>'2100-12-31')throw Error('Tarikh tidak sah.');return date;}
function weekday_(date){return new Date(date+'T12:00:00Z').getUTCDay();}
function today_(){return Utilities.formatDate(new Date(),RELIEF_TZ_,'yyyy-MM-dd');}
function timestamp_(){return Utilities.formatDate(new Date(),RELIEF_TZ_,"yyyy-MM-dd'T'HH:mm:ssXXX");}
function cleanText_(v,max){if(v!=null&&typeof v!=='string')throw Error('Catatan mesti berupa teks.');const s=String(v||'').replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g,'').trim();if(s.length>max)throw Error('Catatan melebihi '+max+' aksara.');return s;}
function safeCell_(v){const s=String(v==null?'':v);return /^[\s]*[=+@-]/.test(s)?"'"+s:s;}
function database_(){const id=PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');if(!id)throw Error('Jalankan setupSistem dahulu.');return SpreadsheetApp.openById(id);}
function assertHeaders_(s,required){const heads=s.getRange(1,1,1,Math.max(s.getLastColumn(),required.length)).getDisplayValues()[0].map(v=>String(v).trim());if(new Set(heads.filter(Boolean)).size!==heads.filter(Boolean).length)throw Error('Header berganda dalam tab '+s.getName()+'.');required.forEach(k=>{if(!heads.includes(k))throw Error('Tab '+s.getName()+' tiada lajur '+k+'. Jangan tukar nama header.');});return heads;}
function readRows_(ss,name,required){const s=ss.getSheetByName(name);if(!s)throw Error('Tab '+name+' tidak ditemui.');const heads=assertHeaders_(s,required);if(s.getLastRow()<2)return [];return s.getRange(2,1,s.getLastRow()-1,heads.length).getDisplayValues().map((r,i)=>{if(!r.some(v=>String(v).trim()!==''))return null;const o={_row:i+2};heads.forEach((k,j)=>{if(k)o[k]=String(r[j]).trim();});return o;}).filter(Boolean);}
function ensureTable_(ss,name,heads){let s=ss.getSheetByName(name);if(!s)s=ss.insertSheet(name);if(!s.getLastRow()){s.getRange(1,1,1,heads.length).setValues([heads]).setBackground('#183d51').setFontColor('#fff').setFontWeight('bold');s.setFrozenRows(1);s.autoResizeColumns(1,heads.length);}else assertHeaders_(s,heads);return s;}
function append_(ss,name,values){const s=ss.getSheetByName(name),schema=RELIEF_SCHEMA_[name],heads=assertHeaders_(s,schema),r=s.getLastRow()+1;plainTextColumns_(s,r,1,1,heads.length);s.getRange(r,1,1,heads.length).setValues([heads.map(h=>{const i=schema.indexOf(h);return i<0?'':safeCell_(values[i]);})]);}
function patch_(ss,name,row,changes){const s=ss.getSheetByName(name),heads=assertHeaders_(s,RELIEF_SCHEMA_[name]),values=s.getRange(row._row,1,1,heads.length).getDisplayValues()[0];heads.forEach((h,i)=>values[i]=safeCell_(Object.prototype.hasOwnProperty.call(changes,h)?changes[h]:values[i]));plainTextColumns_(s,row._row,1,1,heads.length);s.getRange(row._row,1,1,heads.length).setValues([values]);}
/** Sheets Table menerima perubahan format lajur hanya dalam satu lajur pada satu panggilan. */
function plainTextColumns_(sheet,row,column,rowCount,columnCount){
  if(sheet.getMaxRows()<row+rowCount-1)sheet.insertRowsAfter(sheet.getMaxRows(),row+rowCount-1-sheet.getMaxRows());
  if(sheet.getMaxColumns()<column+columnCount-1)sheet.insertColumnsAfter(sheet.getMaxColumns(),column+columnCount-1-sheet.getMaxColumns());
  for(let c=column;c<column+columnCount;c++){
    try{sheet.getRange(row,c,rowCount,1).setNumberFormat('@');}
    catch(e){throw Error('Format tab '+sheet.getName()+', lajur '+c+': '+e.message);}
  }
}
function revision_(c,date){return digest_(JSON.stringify({lessons:c.lessons,teachers:c.teachers,absences:c.absences.filter(a=>a.tarikh===date),reliefs:c.reliefs.filter(r=>r.tarikh===date)}));}
function digest_(s){return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,s,Utilities.Charset.UTF_8).map(n=>('0'+((n+256)%256).toString(16)).slice(-2)).join('');}
