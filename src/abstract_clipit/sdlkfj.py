from abstract_utilities import *
listsi = '''    success:"✅",
    processing:"🔄",
    listening:"📡",
    computing:"🧠",
    waiting:"⏳",
    emitting:"📤",
    ingesting:"📥",
    prune:"🧹",
    connect:"🔌",
    info: "ℹ️",
    warn: "⚠️",
    error: "❌",
    debug: "🔍",'''
listy = []
for each in listsi.split('\n'):
    listy.append(eatAll(each,[' ','\t','\n','']).split(':')[0])
    
input('"'+'" | "'.join(listy)+'"')
