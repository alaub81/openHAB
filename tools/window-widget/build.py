# SPDX-License-Identifier: MIT
# Copyright (c) 2020-2026 Andreas Laub
"""Build a single-fetch window cell with explicit loading states and one view model."""
import copy
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'data/openhab/conf/yaml/widgets/fenster_tueren_cell.yml'


def component(kind, config=None, children=None, slots=None):
    result = {'component': kind, 'config': config or {}}
    if children is not None:
        result['slots'] = {'default': children}
    if slots is not None:
        result['slots'] = slots
    return result


def label(text, css=None, **config):
    if css:
        config['class'] = css
    return component('Label', dict(text=text, **config))


def icon(name, size=17, **config):
    return component('oh-icon', dict(icon=name, width=size, height=size, **config))


def functions(old):
    f = {k: old[k] for k in ['read', 'meta', 'icon', 'brief', 'detail', 'rowColor', 'sorted']}
    # MainUI's Item proxy always returns an object (state '-' while pending).
    # Request/traverse the reactive proxy once, rather than three times per read.
    f['read'] = "=(name) => name ? (items[name].state || '').trim() : ''"
    # The stock Item store uses '-' while state tracking is being established.
    # It is transport readiness, not a real unknown Contact/Alarm state.
    f['rows'] = "=(list,read,meta) => list.filter((s) => s.type === 'Contact').map((s) => ({s:s,m:meta(s)})).map((x) => ({name:x.s.name,label:x.m.config && x.m.config.label || x.s.label || x.s.name,short:(x.m.config && x.m.config.label || x.s.label || x.s.name).replace(/\\s+Fenster\\b/g,'').replace(/\\s+Tür\\b/g,''),state:read(x.s.name),alarm:x.m.value || '',alarmState:read(x.m.value),shared:!!(x.m.config && x.m.config.shared === true),kind:x.m.config && ['window','door'].indexOf(x.m.config.kind) >= 0 ? x.m.config.kind : 'contact'}))"
    f['rank'] = "=(r) => r.alarmState === 'ON' ? 0 : r.state === 'OPEN' ? 1 : (r.state && r.state !== '-' && r.state !== 'CLOSED') || (r.alarm && r.alarmState && r.alarmState !== '-' && r.alarmState !== 'OFF') ? 2 : 3"
    f['isDemo'] = "=(mode) => ['mixed','closed','unknown','loading'].indexOf(mode) >= 0"
    f['demo'] = "=(mode) => mode === 'loading' ? [{name:'demo1',label:'Fenster',short:'Fenster',state:'-',alarm:'demoAlarm',alarmState:'-',shared:false,kind:'window'}] : mode === 'closed' ? [{name:'demo1',label:'Badezimmer Fenster',short:'Badezimmer',state:'CLOSED',alarm:'demoAlarm',alarmState:'OFF',shared:false,kind:'window'},{name:'demo2',label:'Eingang Tür',short:'Eingang',state:'CLOSED',alarm:'',alarmState:'',shared:false,kind:'door'}] : mode === 'unknown' ? [{name:'demo1',label:'Büro Fenster rechts',short:'Büro rechts',state:'UNDEF',alarm:'',alarmState:'',shared:false,kind:'window'}] : mode === 'mixed' ? [{name:'demo1',label:'Badezimmer Fenster',short:'Badezimmer',state:'OPEN',alarm:'demoAlarm',alarmState:'ON',shared:false,kind:'window'},{name:'demo2',label:'Küche Fenster',short:'Küche',state:'OPEN',alarm:'',alarmState:'',shared:false,kind:'window'},{name:'demo3',label:'Terrasse Tür',short:'Terrasse',state:'OPEN',alarm:'',alarmState:'',shared:false,kind:'door'},{name:'demo4',label:'Schlafzimmer Fenster links',short:'Schlafzimmer links',state:'OPEN',alarm:'demoRoom',alarmState:'ON',shared:true,kind:'window'},{name:'demo5',label:'Schlafzimmer Fenster rechts',short:'Schlafzimmer rechts',state:'CLOSED',alarm:'demoRoom',alarmState:'ON',shared:true,kind:'window'}] : []"
    f['summary'] = "=(rows,rank,read,test) => ({rows:rows,test:test,ready:rows.every((r) => r.state && r.state !== '-' && (!r.alarm || r.alarmState && r.alarmState !== '-')) && (test || (!props.alarmGroupItem || read(props.alarmGroupItem) && read(props.alarmGroupItem) !== '-') && (!props.closeAlarmItem || read(props.closeAlarmItem) && read(props.closeAlarmItem) !== '-')),opened:rows.filter((r) => r.state === 'OPEN').length,alarms:rows.filter((r) => r.alarm && r.alarmState === 'ON').map((r) => r.alarm).filter((v,i,a) => a.indexOf(v) === i).length,unknown:rows.filter((r) => r.state && r.state !== '-' && ['OPEN','CLOSED'].indexOf(r.state) < 0 || r.alarm && r.alarmState && r.alarmState !== '-' && ['ON','OFF'].indexOf(r.alarmState) < 0).length,attention:rows.filter((r) => rank(r) < 3).sort((a,b) => rank(a)-rank(b) || a.label.localeCompare(b.label,'de')),group:test ? 'OFF' : read(props.alarmGroupItem),close:test ? 'OFF' : read(props.closeAlarmItem)})"
    f['tone'] = "=(v) => v.alarms > 0 || v.group === 'ON' ? 'var(--f7-color-red)' : v.opened > 0 || v.close === 'ON' ? 'var(--f7-color-orange)' : !v.ready || v.rows.length === 0 || v.unknown > 0 || v.group && v.group !== 'OFF' || v.close && v.close !== 'OFF' ? 'var(--f7-color-gray)' : 'var(--f7-color-green)'"
    return f


def compact():
    head = component('div', {'class': 'contact-head'}, [
        icon('oh:window'),
        label("=loop.view.opened > 0 ? loop.view.opened + ' offen' : loop.view.alarms > 0 || loop.view.group === 'ON' ? 'Alarm aktiv' : loop.view.unknown > 0 || loop.view.group && loop.view.group !== '-' && loop.view.group !== 'OFF' || loop.view.close && loop.view.close !== '-' && loop.view.close !== 'OFF' ? 'Status prüfen' : !loop.view.ready ? 'Status wird geladen' : loop.view.rows.length === 0 ? 'Keine Kontakte' : 'Alles zu'", 'contact-headline'),
        label("=(loop.view.test ? 'TEST · ' : '') + (loop.view.alarms > 0 ? loop.view.alarms + (loop.view.alarms === 1 ? ' Alarm' : ' Alarme') : loop.view.unknown > 0 ? loop.view.unknown + ' unklar' : !loop.view.ready ? 'Lädt …' : loop.view.rows.length + ' Kontakte')", 'contact-badge', style={'color': '=fn.tone(loop.view)'})])
    row = component('div', {'class': 'contact-row', 'title': "=loop.row.label+': '+fn.detail(loop.row)", 'aria-label': "=loop.row.label+': '+fn.detail(loop.row)"}, [
        icon('=fn.icon(loop.row)',14,state='=loop.row.state'),
        label('=loop.row.short','contact-name'),
        label('=fn.brief(loop.row)','contact-state',style={'color':'=fn.rowColor(loop.row)'})])
    attention = component('oh-repeater', {'for':'row','sourceType':'array','in':'=loop.view.attention.slice(0,3)','fragment':True}, [row])
    empty = component('div', {'class':'contact-empty','visible':'=loop.view.attention.length === 0','role':'status','aria-live':'polite'}, [
        icon("=!loop.view.ready ? 'f7:ellipsis_circle' : loop.view.group === 'ON' ? 'oh:alarm' : loop.view.unknown > 0 || loop.view.group && loop.view.group !== 'OFF' || loop.view.close && loop.view.close !== 'OFF' ? 'f7:question_circle' : 'f7:checkmark_shield'",18),
        label("=!loop.view.ready ? 'Status wird geladen …' : loop.view.group === 'ON' ? 'Alarm aktiv · Details öffnen' : loop.view.rows.length === 0 ? 'Keine Kontakte verfügbar' : loop.view.unknown > 0 || loop.view.group && loop.view.group !== 'OFF' || loop.view.close && loop.view.close !== 'OFF' ? 'Alarmstatus unbekannt' : 'Fenster & Türen geschlossen'")])
    footer = label("=!loop.view.ready ? 'Live-Zustände werden geladen' : loop.view.close === 'ON' ? (loop.view.attention.length > 3 ? '+'+(loop.view.attention.length-3)+' · ' : '') + 'Fenster schließen' : loop.view.attention.length > 3 ? '+'+(loop.view.attention.length-3)+' weitere · Details ›' : 'Alle Kontakte · Details ›'", 'contact-footer', style={'grid-row':5,'color':"=loop.view.close === 'ON' ? 'var(--f7-color-orange)' : 'var(--f7-text-color)'"})
    return component('div', {'class':'contact-compact card-opened-fade-out','role':'group','aria-label':"=props.title || 'Fenster und Türen'"}, [head,attention,empty,footer])


def detail():
    entry = component('f7-list-item', {'title':'=loop.row.label','footer':"=loop.row.state === '-' || !loop.row.state || loop.row.alarm && (loop.row.alarmState === '-' || !loop.row.alarmState) ? 'Status wird geladen …' : fn.detail(loop.row)", 'style':{'--f7-list-item-footer-text-color':'=fn.rowColor(loop.row)'}}, slots={'media':[icon('=fn.icon(loop.row)',24,state='=loop.row.state')]})
    return component('div', {'class':'contact-detail'}, [
        label('TESTMODUS · Beispieldaten','contact-notice',visible='=loop.view.test'),
        label('Außen wärmer · Fenster schließen','contact-notice',visible="=loop.view.close === 'ON'",style={'color':'var(--f7-color-orange)'}),
        label('Mindestens ein weiterer Alarm ist aktiv.','contact-notice',visible="=loop.view.group === 'ON' && loop.view.alarms === 0 && loop.view.close !== 'ON'",style={'color':'var(--f7-color-red)'}),
        label('Live-Zustände werden geladen …','contact-notice',visible='=!loop.view.ready'),
        component('f7-list',{'mediaList':True},[component('oh-repeater',{'for':'row','sourceType':'array','in':'=fn.sorted(loop.view.rows,fn.rank)','fragment':True},[entry])]),
        label('Ein Raumalarm gilt gemeinsam für mehrere Kontakte.','contact-notice',visible='=loop.view.rows.some((r) => r.shared)')])


def branch(funcs, content):
    view = component('oh-repeater', {'for':'view','sourceType':'array','in':"=loop.member_idx === 0 ? [fn.summary(fn.isDemo(props.testMode) ? fn.demo(props.testMode) : fn.rows(loop.member_source,fn.read,fn.meta),fn.rank,fn.read,fn.isDemo(props.testMode))] : []",'fragment':True}, [content])
    source = component('oh-repeater',{'for':'member','sourceType':'itemsInGroup','groupItem':'=props.contactGroup','fetchMetadata':'contactOverview','cacheSource':True,'fragment':True},[view])
    return component('oh-context',{'functions':copy.deepcopy(funcs)},[source])


def build(doc):
    w=doc['widgets']['fenster_tueren_cell']
    # Avoid waiting for Safari/WebView transition completion before oh-cell
    # mounts its expanded content; the native nonanimated path opens instantly.
    w['config']['animate']=False
    old=w['slots']['background'][0]['config']['functions']
    funcs=functions(old)
    background=branch(funcs,compact())
    loading=component('div',{'class':'contact-initial card-opened-fade-out','role':'status','aria-live':'polite'},[icon('f7:ellipsis_circle',20),label('Status wird geladen …')])
    source=background['slots']['default'][0]
    background['slots']['default']=[component('div',{'class':'contact-shell card-opened-fade-out'},[loading,source])]
    w['slots']={'background':[background],'default':[branch(funcs,detail())]}
    css=w['config']['stylesheet']
    marker='/* single-fetch-loading */'
    if marker in css:css=css.split(marker)[0]
    w['config']['stylesheet']=css.rstrip()+'''\n/* single-fetch-loading */
.contact-shell {position:absolute;inset:0;background:var(--f7-card-bg-color);pointer-events:none;}
.contact-initial {position:absolute;inset:0;display:flex;align-items:center;justify-content:center;gap:8px;font-size:12px;color:var(--f7-text-color);opacity:.8;}
.contact-shell:has(.contact-compact) .contact-initial {display:none;}
'''
    for param in w['props']['parameters']:
        if param['name']=='equipmentGroup':
            param['required']=False
            param['description']='Kompatibilitätsparameter; Symboltypen stehen nun in contactOverview.config.kind. Keine zusätzliche Geräteabfrage.'
        if param['name']=='testMode' and not any(o['value']=='loading' for o in param['options']):
            param['options'].append({'value':'loading','label':'Test – Zustände werden geladen'})
    return doc


if __name__=='__main__':
    doc=json.loads(subprocess.check_output(['ruby','-ryaml','-rjson','-e','puts JSON.generate(YAML.load_file(ARGV[0]))',str(TARGET)],text=True))
    result=build(doc)
    yaml=subprocess.check_output(['ruby','-ryaml','-rjson','-e','puts JSON.parse(STDIN.read).to_yaml'],input=json.dumps(result,ensure_ascii=False),text=True)
    TARGET.write_text(yaml)
