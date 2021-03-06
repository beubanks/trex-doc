#! /usr/bin/env python
# encoding: utf-8
# hhaim, 2014 (IL) base on WAF book

"""
call 'waf --targets=waf.pdf' or use 'waf list' to see the targets available
"""

VERSION='0.0.1'
APPNAME='wafdocs'

import os, re, shutil
import shlex
import subprocess


top = '.'
out = 'build'

re_xi = re.compile('''^(include|image)::([^.]*.(asciidoc|\\{PIC\\}))\[''', re.M)
def ascii_doc_scan(self):
    p = self.inputs[0].parent
    node_lst = [self.inputs[0]]
    seen = []
    depnodes = []
    while node_lst:
        nd = node_lst.pop(0)
        if nd in seen: continue
        seen.append(nd)

        code = nd.read()
        for m in re_xi.finditer(code):
            name = m.group(2)
            if m.group(3) == '{PIC}':

                ext = '.eps'
                if self.generator.rule.rfind('A2X') > 0:
                    ext = '.png'

                k = p.find_resource(name.replace('{PIC}', ext))
                if k:
                    depnodes.append(k)
            else:
                k = p.find_resource(name)
                if k:
                    depnodes.append(k)
                    node_lst.append(k)
    return [depnodes, ()]
        
        

import re
def scansize(self):
    name = 'image::%s\\{PIC\\}\\[.*,(width|height)=(\\d+)' % self.inputs[0].name[:-4]
    re_src = re.compile(name)
    lst = self.inputs[0].parent.get_src().ant_glob('*.txt')
    for x in lst:
        m = re_src.search(x.read())
        if m:
            val = str(int(1.6 * int(m.group(2))))
            if m.group(1) == 'width':
                w = val
                h = "800"
            else:
                w = "800"
                h = val

            ext = self.inputs[0].name[-3:]
            if ext == 'eps':
                code = '-geometry %sx%s' % (w, h)
            elif ext == 'dia':
                if m.group(1) == 'width':
                    h = ''
                else:
                    w = ''
                code = '--size %sx%s' % (w, h)
            else:
                code = '-Gsize="%s,%s"' % (w, h)
            break
    else:
        return ([], '')

    return ([], code)

def options(opt):
    opt.add_option('--exe', action='store_true', default=False, help='Execute the program after it is compiled')

def configure(conf):
    conf.find_program('asciidoc', path_list='/usr/bin/', var='ASCIIDOC')
    conf.find_program('sphinx-build', path_list='/usr/local/bin/', var='SPHINX')
    pass;

def convert_to_pdf(task):
    input_file = task.outputs[0].abspath()
    out_dir = task.outputs[0].parent.get_bld().abspath()
    os.system('a2x --no-xmllint -v -f pdf  -d  article %s -D %s ' %(task.inputs[0].abspath(),out_dir ) )
    return (0)

def convert_to_pdf_book(task):
    input_file = task.outputs[0].abspath()
    out_dir = task.outputs[0].parent.get_bld().abspath()
    os.system('a2x --no-xmllint -v -f pdf  -d book %s -D %s ' %(task.inputs[0].abspath(),out_dir ) )
    return (0)


def ensure_dir(f):
    if not os.path.exists(f):
        os.makedirs(f)
    

def my_copy(task):
    input_file=task.outputs[0].abspath()
    out_dir=task.outputs[0].parent.get_bld().abspath()
    ensure_dir(out_dir)
    shutil.copy2(input_file, out_dir+ os.sep+task.outputs[0].name)
    return (0)


def do_visio(bld):
    for x in bld.path.ant_glob('visio\\*.vsd'):
        tg = bld(rule='${VIS} -i ${SRC} -o ${TGT} ', source=x, target=x.change_ext('.png'))

def get_trex_core_git():
    trex_core_git_path = os.path.join(os.getcwd(), os.pardir, "trex-core")
    if not os.path.isdir(trex_core_git_path):
        trex_core_git_path = os.getenv('TREX_CORE_GIT', None)
    return trex_core_git_path

def parse_hlt_args(task):
    trex_core_git_path = get_trex_core_git()
    if not trex_core_git_path:
        return 1
    hltapi_path = os.path.abspath(os.path.join(trex_core_git_path, 'scripts', 'automation', 'trex_control_plane', 'stl', 'trex_stl_lib', 'trex_stl_hltapi.py'))
    header = ['[options="header",cols="<.^1,^.^1,9<.^e"]', '|=================', '^| Argument | Default ^| Comment']
    footer = ['|=================\n']
    hlt_asciidoc = []
    category_regexp = '^(\S+)_kwargs = {$'
    comment_line_regexp = '^\s*#\s*(.+)$'
    arg_line_regexp = "^\s*'([^']+)':\s*'?([^,']+)'?,\s*#?\s*(.+)?$"
    if not os.path.exists(hltapi_path):
        raise Exception('Could not find hltapi file: %s' % hltapi_path)
    with open(hltapi_path) as f:
        in_args = False
        for line in f.read().splitlines():
            if not in_args:
                if line.startswith('import'):
                    break
                category_line = re.match(category_regexp, line)
                if category_line:
                    hlt_asciidoc.append('\n===== %s\n' % category_line.group(1))
                    hlt_asciidoc += header
                    in_args = True
                continue
            comment_line = re.match(comment_line_regexp, line)
            if comment_line:
                hlt_asciidoc.append('3+^.^s| %s' % comment_line.group(1).replace('|', '\|'))
                continue
            arg_line = re.match(arg_line_regexp, line)
            if arg_line:
                arg, default, comment = arg_line.groups()
                hlt_asciidoc.append('| %s | %s | %s' % (arg, default, comment.replace('|', '\|') if comment else ''))
                continue
            if line == '}':
                hlt_asciidoc += footer
                in_args = False
    if not len(hlt_asciidoc):
        raise Exception('Parsing of hltapi args failed')
    with open('build/hlt_args.asciidoc', 'w') as f:
        f.write('\n'.join(hlt_asciidoc))
    return 0

def build_cp_docs (task):
    out_dir = task.outputs[0].abspath()
    export_path = os.path.join(os.getcwd(), 'build', 'cp_docs')
    trex_core_git_path = get_trex_core_git()
    if not trex_core_git_path: # there exists a default directory or the desired ENV variable.
        return 1
    trex_core_docs_path = os.path.abspath(os.path.join(trex_core_git_path, 'scripts', 'automation', 'trex_control_plane', 'doc'))
    build_doc_cmd = shlex.split("/usr/local/bin/sphinx-build -W -b {bld} {src} {dst}".format(
        bld= "html", 
        src= ".", 
        dst= out_dir)
    )
    return subprocess.call(build_doc_cmd, cwd = trex_core_docs_path)

def build_stl_cp_docs (task):
    out_dir = task.outputs[0].abspath()
    export_path = os.path.join(os.getcwd(), 'build', 'cp_stl_docs')
    trex_core_git_path = get_trex_core_git()
    if not trex_core_git_path: # there exists a default directory or the desired ENV variable.
        return 1
    trex_core_docs_path = os.path.abspath(os.path.join(trex_core_git_path, 'scripts', 'automation', 'trex_control_plane', 'doc_stl'))
    build_doc_cmd = shlex.split("/usr/local/bin/sphinx-build -W -b {bld} {src} {dst}".format(
        bld= "html", 
        src= ".", 
        dst= out_dir)
    )
    return subprocess.call(build_doc_cmd, cwd = trex_core_docs_path)



def build_cp(bld,dir,root,callback):
    export_path = os.path.join(os.getcwd(), 'build', dir)
    trex_core_git_path = get_trex_core_git()
    if not trex_core_git_path: # there exists a default directory or the desired ENV variable.
        raise NameError("Environment variable 'TREX_CORE_GIT' is not defined.")
    trex_core_docs_path = os.path.join(trex_core_git_path, 'scripts', 'automation', 'trex_control_plane', root, 'index.rst')
    bld(rule=callback,target = dir)



def build(bld):
    bld(rule=my_copy, target='symbols.lang')

    for x in bld.path.ant_glob('images\\**\**.png'):
            bld(rule=my_copy, target=x)
            bld.add_group() 


    for x in bld.path.ant_glob('yaml\\**\**.yaml'):
            bld(rule=my_copy, target=x)
            bld.add_group() 


    for x in bld.path.ant_glob('video\\**\**.mp4'):
            bld(rule=my_copy, target=x)
            bld.add_group() 


    for x in bld.path.ant_glob('images\\**\**.jpg'):
        bld(rule=my_copy, target=x)
        bld.add_group() 

    bld(rule=my_copy, target='my_chart.js')

    build_cp(bld,'hlt_args.asciidoc','stl/trex_stl_lib', parse_hlt_args)

    bld.add_group() # separator, the documents may require any of the pictures from above

    if os.path.exists('build/hlt_args.asciidoc'):
        bld.add_manual_dependency(
            bld.path.find_node('draft_trex_stateless.asciidoc'),
            'build/hlt_args.asciidoc')

    bld(rule='${ASCIIDOC}  -b deckjs -o ${TGT} ${SRC[0].abspath()}',
        source='trex_config.asciidoc ', target='trex_config_guide.html', scan=ascii_doc_scan)


    bld(rule='${ASCIIDOC}  -b deckjs -o ${TGT} ${SRC[0].abspath()}',
        source='trex_preso.asciidoc ', target='trex_preso.html', scan=ascii_doc_scan)

    bld(rule='${ASCIIDOC}  -a stylesheet=${SRC[1].abspath()} -a  icons=true -a max-width=55em  -o ${TGT} ${SRC[0].abspath()}',
        source='release_notes.asciidoc waf.css', target='release_notes.html', scan=ascii_doc_scan)
                

    bld(rule='${ASCIIDOC} -a docinfo -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2 -a max-width=55em  -d book   -o ${TGT} ${SRC[0].abspath()}',
        source='trex_book.asciidoc waf.css', target='trex_manual.html', scan=ascii_doc_scan)

    bld(rule='${ASCIIDOC} -a docinfo -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2  -a max-width=55em  -d book   -o ${TGT} ${SRC[0].abspath()}',
        source='draft_trex_stateless.asciidoc waf.css', target='draft_trex_stateless.html', scan=ascii_doc_scan)

    bld(rule='${ASCIIDOC} -a docinfo -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2  -a max-width=55em  -d book   -o ${TGT} ${SRC[0].abspath()}',
        source='draft_trex_stateless_moved1.asciidoc waf.css', target='draft_trex_stateless1.html', scan=ascii_doc_scan)

    bld(rule=convert_to_pdf_book,source='trex_book.asciidoc waf.css', target='trex_book.pdf', scan=ascii_doc_scan)

    bld(rule=convert_to_pdf_book,source='draft_trex_stateless.asciidoc waf.css', target='draft_trex_stateless.pdf', scan=ascii_doc_scan)
                

    bld(rule=convert_to_pdf_book,source='trex_vm_manual.asciidoc waf.css', target='trex_vm_manual.pdf', scan=ascii_doc_scan)

    bld(rule=convert_to_pdf_book,source='trex_control_plane_peek.asciidoc waf.css', target='trex_control_plane_peek.pdf', scan=ascii_doc_scan)
    
    bld(rule=convert_to_pdf_book, source='trex_control_plane_design_phase1.asciidoc waf.css', target='trex_control_plane_design_phase1.pdf', scan=ascii_doc_scan)

    bld(rule='${ASCIIDOC}   -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2 -a max-width=55em  -o ${TGT} ${SRC[0].abspath()}',
        source='trex_vm_manual.asciidoc waf.css', target='trex_vm_manual.html', scan=ascii_doc_scan)

    bld(rule='${ASCIIDOC}   -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2 -a max-width=55em  -o ${TGT} ${SRC[0].abspath()}',
        source='vm_doc.asciidoc waf.css', target='vm_doc.html', scan=ascii_doc_scan)

    bld(rule='${ASCIIDOC}   -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2 -a max-width=55em  -o ${TGT} ${SRC[0].abspath()}',
        source='packet_builder_yaml.asciidoc waf.css', target='packet_builder_yaml.html', scan=ascii_doc_scan)
        
    bld(rule='${ASCIIDOC}   -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2 -a max-width=55em  -o ${TGT} ${SRC[0].abspath()}',
        source='trex_rpc_server_spec.asciidoc waf.css', target='trex_rpc_server_spec.html', scan=ascii_doc_scan)

    bld(rule='${ASCIIDOC}   -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2 -a max-width=55em  -o ${TGT} ${SRC[0].abspath()}',
        source='trex_control_plane_design_phase1.asciidoc waf.css', target='trex_control_plane_design_phase1.html', scan=ascii_doc_scan)
        
    bld(rule='${ASCIIDOC}   -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2 -a max-width=55em  -o ${TGT} ${SRC[0].abspath()}',
        source='trex_control_plane_peek.asciidoc waf.css', target='trex_control_plane_peek.html', scan=ascii_doc_scan)

    bld(rule='${ASCIIDOC}   -a stylesheet=${SRC[1].abspath()} -a  icons=true -a toc2 -a max-width=55em  -o ${TGT} ${SRC[0].abspath()}',
        source='trex_console.asciidoc waf.css', target='trex_console.html', scan=ascii_doc_scan)

    build_cp(bld,'cp_docs','doc',build_cp_docs)

    build_cp(bld,'cp_stl_docs','doc_stl',build_stl_cp_docs)


class Env(object):
    @staticmethod
    def get_env(name) :
        s= os.environ.get(name);
        if s == None:
            print "You should define $",name
            raise Exception("Env error");
        return (s);
    
    @staticmethod
    def get_release_path () :
        s= Env().get_env('TREX_LOCAL_PUBLISH_PATH');
        s +=get_build_num ()+"/"
        return  s;

    @staticmethod
    def get_remote_release_path () :
        s= Env().get_env('TREX_REMOTE_PUBLISH_PATH');
        return  s;

    @staticmethod
    def get_local_web_server () :
        s= Env().get_env('TREX_WEB_SERVER');
        return  s;

    # extral web 
    @staticmethod
    def get_trex_ex_web_key() :
        s= Env().get_env('TREX_EX_WEB_KEY');
        return  s;

    @staticmethod
    def get_trex_ex_web_path() :
        s= Env().get_env('TREX_EX_WEB_PATH');
        return  s;

    @staticmethod
    def get_trex_ex_web_user() :
        s= Env().get_env('TREX_EX_WEB_USER');
        return  s;

    @staticmethod
    def get_trex_ex_web_srv() :
        s= Env().get_env('TREX_EX_WEB_SRV');
        return  s;

    @staticmethod
    def get_trex_core() :
        s= Env().get_env('TREX_CORE_GIT');
        return  s;



def release(bld):
    # copy all the files to our web server 
    core_dir = Env().get_trex_core()
    release_dir = core_dir +"/scripts/doc/";
    os.system('mkdir -p '+release_dir)
    os.system('cp -rv build/release_notes.* '+ release_dir)


def publish(bld):
    # copy all the files to our web server 
    remote_dir = "%s:%s" % ( Env().get_local_web_server(), Env().get_remote_release_path ()+'../doc/')
    os.system('rsync -av --rsh=ssh build/ %s' % (remote_dir))


def publish_ext(bld):
   from_ = 'build/'
   os.system('rsync -avz -e "ssh -i %s" --rsync-path=/usr/bin/rsync %s %s@%s:%s/doc/' % (Env().get_trex_ex_web_key(),from_, Env().get_trex_ex_web_user(),Env().get_trex_ex_web_srv(),Env().get_trex_ex_web_path() ) )
   




         
               

