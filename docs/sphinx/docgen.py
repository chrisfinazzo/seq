#%%
import json
import itertools
import os
import os.path
import sys
import subprocess as sp
import collections
from pprint import pprint

from sphinxcontrib.napoleon.docstring import GoogleDocstring
from sphinxcontrib.napoleon import Config

napoleon_config=Config(napoleon_use_param=True,napoleon_use_rtype=True)

root=os.path.abspath(sys.argv[1])
print(f"Generating documentation for {root}...")


# 1. Call seqc -docstr and get a documentation in JSON format
def load_json(directory):
    # Get all seq files in the directory
    files=[]
    for root,_,items in os.walk(directory):
        for f in items:
            if f.endswith('.seq'):
                files.append(os.path.abspath(os.path.join(root,f)))
    files='\n'.join(files)
    s=sp.run(['../../build/seqc','-doc','-'],stdout=sp.PIPE,input=files.encode('utf-8'))
    if s.returncode!=0:
        raise ValueError('seqc failed')
    return json.loads(s.stdout.decode('utf-8'))


j=load_json(root)
print(f" - Done with seqc")
# with open('x.json','w') as f:
#     json.dump(j,f,indent=2)

# 2. Get the list of modules and create the documentation tree
modules={k:v["path"] for k,v in j.items() if v["kind"]=="module"}
prefix=os.path.commonprefix(list(modules.values()))
parsed_modules=collections.defaultdict(set)
os.system("rm -rf stdlib/*")
for mid,module in modules.items():
    while module!=root:
        directory,name=os.path.split(module)
        print(root,mid,module)
        directory=os.path.relpath(directory,root)  # remove the prefix
        os.makedirs(f"stdlib/{directory}",exist_ok=True)
        if name.endswith('.seq'):
            name=name[:-4]
        if name!='__init__':
            parsed_modules[directory].add((name,mid))
        module=os.path.split(module)[0]
for directory,modules in parsed_modules.items():
    module=directory.replace('/','.')
    with open(f'stdlib/{directory}/index.rst','w') as f:
        if module!='.':
            print(f".. seq:module:: {module}\n",file=f)
            print(f"{module}",file=f)
        else:
            print("Standard Library Reference",file=f)
        print(f"========\n",file=f)

        print(".. toctree::\n",file=f)
        for m in sorted(set(m for m,_ in modules)):
            if os.path.isdir(f'{root}/{directory}/{m}'):
                print(f"   {m}/index",file=f)
            else:
                print(f"   {m}",file=f)
print(f" - Done with directory tree")


def parse_docstr(s,level=1):
    """Parse docstr s and indent it with level spaces"""
    lines=GoogleDocstring(s,napoleon_config).lines()
    if isinstance(lines,str):  # Napoleon failed
        s=s.split('\n')
        while s and s[0]=='':
            s=s[1:]
        while s and s[-1]=='':
            s=s[:-1]
        if not s:
            return ''
        i=0
        indent=len(list(itertools.takewhile(lambda i:i==' ',s[0])))
        lines=[l[indent:] for l in s]
    return '\n'.join(('   '*level)+l for l in lines)


def parse_type(a):
    """Parse type signature"""
    s=''
    if isinstance(a,list):
        head,tail=a[0],a[1:]
    else:
        head,tail=a,[]
    s+=j[head]["name"] if head[0].isdigit() else head
    if tail:
        for ti,t in enumerate(tail):
            s+="[" if not ti else ", "
            s+=parse_type(t)
        s+="]"
    return s


def parse_fn(v,skip_self=False,skip_braces=False):
    """Parse function signature after the name"""
    s=""
    if 'generics' in v and v['generics']:
        s+=f'[{", ".join(v["generics"])}]'
    if not skip_braces:
        s+="("
    cnt=0
    for ai,a in enumerate(v['args']):
        if ai==0 and a["name"]=="self" and skip_self:
            continue
        s+="" if not cnt else ", "
        cnt+=1
        s+=f'{a["name"]}'
        if "type" in a:
            s+=" : "+parse_type(a["type"])
        if "default" in a:
            s+=" = "+a["default"]+""
    if not skip_braces:
        s+=')'
    if "ret" in v:
        s+=" -> "+parse_type(v["ret"])
    # if "extern" in v:
    #     s += f" (_{v['extern']} function_)"
    # s += "\n"
    return s


# 3. Create documentation for each module
for directory,(name,mid) in {(d,m) for d,mm in parsed_modules.items() for m in mm}:
    module=directory.replace('/','.')+f".{name}"

    file,mode=f'stdlib/{directory}/{name}.rst','w'
    if os.path.isdir(f'{root}/{directory}/{name}'):
        continue
    if name=='__init__':
        file,mode=f'stdlib/{directory}/index.rst','a'
    with open(file,mode) as f:
        print(f".. seq:module:: {module}\n",file=f)
        print(f":seq:mod:`{module}`",file=f)
        print("-"*(len(module)+11)+"\n",file=f)
        directory_prefix=directory+'/' if directory!='.' else ''
        print(f"Source code: `{directory_prefix}{name}.seq <https://github.com/seq-lang/seq/blob/master/stdlib/{directory}/{name}.seq>`_\n",file=f)
        if 'doc' in j[mid]:
            print(parse_docstr(j[mid]['doc']),file=f)

        for i in j[mid]['children']:
            v=j[i]

            if v['kind']=='class' and v['type']=='extension':
                v['name']=j[v['parent']]['name']
            if v['name'].startswith('_'):
                continue

            if v['kind']=='class':
                if v['name'].endswith('Error'):
                    v["type"]="exception"
                f.write(f'.. seq:{v["type"]}:: {v["name"]}')
                if 'generics' in v and v['generics']:
                    f.write(f'[{",".join(v["generics"])}]')
            elif v['kind']=='function':
                f.write(f'.. seq:function:: {v["name"]}{parse_fn(v)}')
            elif v['kind']=='variable':
                f.write(f'.. seq:data:: {v["name"]}')
            # if v['kind'] == 'class' and v['type'] == 'extension':
            #     f.write(f'**`{getLink(v["parent"])}`**')
            # else:
            # f.write(f'{m}.**`{v["name"]}`**')
            f.write("\n")

            # f.write("\n")
            # if v['kind'] == 'function' and 'attrs' in v and v['attrs']:
            #     f.write("**Attributes:**" + ', '.join(f'`{x}`' for x in v['attrs']))
            #     f.write("\n")
            if 'doc' in v:
                f.write("\n"+parse_docstr(v['doc'])+"\n")
            f.write("\n")

            if v['kind']=='class':
                # if 'args' in v and any(c['name'][0] != '_' for c in v['args']):
                #     f.write('#### Arguments:\n')
                #     for c in v['args']:
                #         if c['name'][0] == '_':
                #             continue
                #         f.write(f'- **`{c["name"]} : `**')
                #         f.write(parse_type(c["type"]) + "\n")
                #         if 'doc' in c:
                #             f.write(parse_docstr(c['doc'], 1) + "\n")
                #         f.write("\n")

                mt=[c for c in v['members'] if j[c]['kind']=='function']

                props=[c for c in mt if 'property' in j[c].get('attrs',[])]
                if props:
                    print('   **Properties:**\n',file=f)
                    for c in props:
                        v=j[c]
                        f.write(f'      .. seq:attribute:: {v["name"]}\n')
                        if 'doc' in v:
                            f.write("\n"+parse_docstr(v['doc'],4)+"\n\n")
                        f.write("\n")

                magics=[c for c in mt if len(j[c]['name'])>4 and j[c]['name'].startswith('__') and j[c]['name'].endswith('__')]
                if magics:
                    print('   **Magic methods:**\n',file=f)
                    for c in magics:
                        v=j[c]
                        f.write(f'      .. seq:method:: {v["name"]}{parse_fn(v,True)}\n')
                        f.write('         :noindex:\n')
                        if 'doc' in v:
                            f.write("\n"+parse_docstr(v['doc'],4)+"\n\n")
                        f.write("\n")
                methods=[c for c in mt if j[c]['name'][0]!='_' and c not in props]
                if methods:
                    print('   **Methods:**\n',file=f)
                    for c in methods:
                        v=j[c]
                        f.write(f'      .. seq:method:: {v["name"]}{parse_fn(v,True)}\n')
                        if 'doc' in v:
                            f.write("\n"+parse_docstr(v['doc'],4)+"\n\n")
                        f.write("\n")
            f.write("\n\n")

        f.write("\n\n")
print(f" - Done with modules")
