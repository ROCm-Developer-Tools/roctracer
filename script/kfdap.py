#!/usr/bin/python
import os, sys, re

OUT='inc/kfd_prof_str' 
OUT_CPP='src/core/kfd_prof_str'
API_TABLES_H = 'hsakmt.h' 
API_HEADERS_H = ( 
  ('HSAKMTAPI', API_TABLES_H), 
  ('HSAKMTAPI', API_TABLES_H),
)

LICENSE = \
'/*\n' + \
'Copyright (c) 2018 Advanced Micro Devices, Inc. All rights reserved.\n' + \
'\n' + \
'Permission is hereby granted, free of charge, to any person obtaining a copy\n' + \
'of this software and associated documentation files (the "Software"), to deal\n' + \
'in the Software without restriction, including without limitation the rights\n' + \
'to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n' + \
'copies of the Software, and to permit persons to whom the Software is\n' + \
'furnished to do so, subject to the following conditions:\n' + \
'\n' + \
'The above copyright notice and this permission notice shall be included in\n' + \
'all copies or substantial portions of the Software.\n' + \
'\n' + \
'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n' + \
'IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n' + \
'FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE\n' + \
'AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n' + \
'LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n' + \
'OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN\n' + \
'THE SOFTWARE.\n' + \
'*/\n'

#############################################################
# Error handler
def fatal(module, msg):
  print >>sys.stderr, module + ' Error: "' + msg + '"'
  sys.exit(1)

# Get next text block
def NextBlock(pos, record): 
  print ("record and pos", record, pos);
  if len(record) == 0: return pos

  space_pattern = re.compile(r'(\s+)')
  word_pattern = re.compile(r'([\w\*]+\[*\]*)')
  if record[pos] != '(':
    m = space_pattern.match(record, pos)
    if not m:
      m = word_pattern.match(record, pos)
    if m:
      return pos + len(m.group(1))
    else:
      fatal('NextBlock', "bad record '" + record + "' pos(" + str(pos) + ")")
  else:
    count = 0
    for index in range(pos, len(record)):
      if record[index] == '(':
        count = count + 1
      elif record[index] == ')':
        count = count - 1
        if count == 0:
          index = index + 1
          break
    if count != 0:
      fatal('NextBlock', "count is not zero (" + str(count) + ")")
    if record[index - 1] != ')':
      fatal('NextBlock', "last char is not ')' '" + record[index - 1] + "'")
    return index

#############################################################
# API table parser class
class API_TableParser:
  def fatal(self, msg):
    fatal('API_TableParser', msg)

  def __init__(self, header, name, full_fct, get_includes):
    self.name = name
    self.full_fct = full_fct
    self.get_includes = get_includes

    if not os.path.isfile(header):
      self.fatal("file '" + header + "' not found")

    self.inp = open(header, 'r')

    print ("NAME", name);
    self.beg_pattern = re.compile(name) 
    self.end_pattern = re.compile('.*\)\s*;\s*$'); 
    self.inc_pattern = re.compile('\s*#include\s+(.*)$');
    self.array = []
    self.parse()

  # normalizing a line
  def norm_line(self, line):
    return re.sub(r'^\s+', r' ', line)

  def fix_comment_line(self, line):
    return re.sub(r'\/\/.*', r'', line) 

  def remove_ret_line(self, line):
    return re.sub(r'\n', r'', line) 

  # check for start record
  def is_start(self, record):
    return self.beg_pattern.match(record)

  # check for end record
  def is_end(self, record):
    return self.end_pattern.match(record)

  # check for declaration entry record
  def is_entry(self, record):
    return re.match(r'^\s*HSAKMTAPI\s*(.*)\s*\((.*)\)', record) 

  def is_include(self, record):
    return self.inc_pattern.search(record)

  # parse method
  def parse(self):
    active = 0
    record = "";
    cumulate=0;
    self.full_fct={}
    self.get_includes=[]
    for line in self.inp.readlines():
      print ("LINE before", line)
      m=self.is_include(line)
      if m:
          print ("INCLUDE, FILE", line,m.group(1))
          self.get_includes.append(m.group(1))
      line = self.norm_line(line)
      line = self.fix_comment_line(line)

      print ("LINE", line)

      if cumulate == 1: record += " " + line; print ("after concat", record);
      else: record = line;
      if self.is_start(line): cumulate = 1; continue;
      if self.is_end(line): record = self.remove_ret_line(record); print ("Pattern found", record); cumulate=0; active =1;

      else: continue;
      if active != 0:
        m = self.is_entry(record)
        if m:
          mycall_full="void " +m.group(1)+' ('+m.group(2)+')'
          mycall=m.group(1)
          print ("APPEND", mycall)
          self.full_fct[mycall]=mycall_full
          self.array.append(mycall) 

#############################################################
# APIaKmtGetNodePropertiesdeclaration parser class
class API_DeclParser:
  def fatal(self, msg):
    fatal('API_DeclParser', msg)

  def __init__(self, header, array, data, full_fct, get_includes):
    if not os.path.isfile(header):
      self.fatal("file '" + header + "' not found")

    self.inp = open(header, 'r')

    self.end_pattern = re.compile('\)\s*;\s*$')
    self.data = data
    for call in array:
      if call in data:
        self.fatal(call + ' is already found')
      print("calling parse 2");
      self.parse(call,full_fct,get_includes)

  # api record filter
  #def api_filter(self, record):
    #record = re.sub(r'\sKFD_API\s', r' ', record)
    #record = re.sub(r'\sKFD_DEPRECATED\s', r' ', record)
    #return record

  # check for start record
  def is_start(self, call, record):
    return re.search('\s*' + call + '\s*\(', record)

  # check for API method record
  def is_api(self, call, record):
    #record = self.api_filter(record)
    #return re.match('\s+\S+\s+' + call + '\s*\(', record)
    return re.match('\s*' + call + '\s*\(', record)


  # check for end record
  def is_end(self, record):
    return self.end_pattern.search(record)

  # parse method args
  def get_args(self, record):
    print ("RECORD", record);
    struct = {'ret': '', 'args': '', 'astr': {}, 'alst': [], 'tlst': []}
    record = re.sub(r'^\s+', r'', record)
    record = re.sub(r'\s*(\*+)\s*', r'\1 ', record)
    rind = NextBlock(0, record) 
    struct['ret'] = record[0:rind]
    pos = record.find('(')
    print ("POS", pos)
    end = NextBlock(pos, record);
    print ("POSEND", end)
    args = record[pos:end]
    print ("ARGS", args)
    args = re.sub(r'^\(\s*', r'', args)
    args = re.sub(r'\s*\)$', r'', args)
    args = re.sub(r'\s*,\s*', r',', args)
    print ("ARGSAFTER", args)
    struct['args'] = re.sub(r',', r', ', args)
    if args == "void":
      return struct
        
    if len(args) == 0: return struct

    pos = 0
    args = args + ','
    while pos < len(args):
      ind1 = NextBlock(pos, args) # type
      ind2 = NextBlock(ind1, args) # space
      if args[ind2] != '(':
        while ind2 < len(args):
          end = NextBlock(ind2, args)
          if args[end] == ',': break
          else: ind2 = end
        name = args[ind2:end]
      else:
        ind3 = NextBlock(ind2, args) # field
        m = re.match(r'\(\s*\*\s*(\S+)\s*\)', args[ind2:ind3])
        if not m:
          self.fatal("bad block3 '" + args + "' : '" + args[ind2:ind3] + "'")
        name = m.group(1)
        end = NextBlock(ind3, args) # the rest
      item = args[pos:end]
      struct['astr'][name] = item
      struct['alst'].append(name)
      struct['tlst'].append(item)
      if args[end] != ',':
        self.fatal("no comma '" + args + "'")
      pos = end + 1

    return struct

  #def is_mycall(self, record):
  #  return re.match(r'^\s*(.*)\s*\((.*)\)', record)

  # parse given api
  def parse(self, call, full_fct,get_includes):
    print ("CALL, full_fct length", call, len(full_fct));
    if call in full_fct: 
      self.data[call] = self.get_args(full_fct[call])
    else:
      self.data[call] = self.get_args(call)

    #m = self.is_mycall(call)
    #if m:
      #self.data[call]=m.group(2)

  # parse given api
  def parse_old(self, call):
    print ("CALL", call);
    record = ''
    active = 0
    found = 0
    api_name = ''
    prev_line = ''

    self.inp.seek(0)
    for line in self.inp.readlines():
      print ("LINE2", line);
      record += ' ' + line[:-1]
      record = re.sub(r'^\s*', r' ', record)

      if active == 0:
        if self.is_start(call, record):
          active = 1
          m = self.is_api(call, record)
          if not m:
            record = ' ' + prev_line + ' ' + record
            m = self.is_api(call, record)
            if not m:
              self.fatal("bad api '" + line + "'")

      if active == 1:
        if self.is_end(record):
          self.data[call] = self.get_args(record)
          active = 0
          found = 0

      if active == 0: record = ''
      prev_line = line

#############################################################
# API description parser class
class API_DescrParser:
  def fatal(self, msg):
    fatal('API_DescrParser', msg)

  def __init__(self, out_file, kfd_dir, api_table_h, api_headers, license):
    out_macro = re.sub(r'[\/\.]', r'_', out_file.upper()) + '_'

    self.content = ''
    self.content_cpp = ''

    self.api_names = []
    self.api_calls = {}
    self.api_rettypes = set()
    self.api_id = {}
    
    get_includes = []
    api_data = {}
    full_fct = {}
    api_list = []
    ns_calls = []

    for i in range(0, len(api_headers)):
      (name, header) = api_headers[i]
      
      if i < len(api_headers) - 1: 
        api = API_TableParser(kfd_dir + api_table_h, name, full_fct, get_includes)
        full_fct = api.full_fct
        get_includes = api.get_includes
        print ("SIZE", len(full_fct))
        api_list = api.array
        self.api_names.append(name)
        self.api_calls[name] = api_list
      else:
        api_list = ns_calls
        ns_calls = []

      for call in api_list:
        print ("CALL", call);
        if call in api_data:
          self.fatal("call '"  + call + "' is already found")

      print ("DATA", api_data);
      API_DeclParser(kfd_dir + header, api_list, api_data, full_fct,get_includes)

      for call in api_list:
        if not call in api_data:
          # Not-supported functions
          ns_calls.append(call)
        else:
          # API ID map
          self.api_id[call] = 'KFD_API_ID_' + call
          # Return types
          self.api_rettypes.add(api_data[call]['ret'])

    self.api_rettypes.discard('void')
    self.api_data = api_data
    self.ns_calls = ns_calls

    self.content += "// automatically generated\n\n" + license + '\n'
    
    self.content += "/////////////////////////////////////////////////////////////////////////////\n"
    for call in self.ns_calls:
      self.content += '// ' + call + ' was not parsed\n'
    self.content += '\n'
    self.content += '#ifndef ' + out_macro + 'H_' + '\n'
    self.content += '#define ' + out_macro + 'H_' + '\n'

    self.content += '\n'
    #for incl in get_includes: NOT NEEDED
    #  self.content += '#include ' + incl + '\n'

    self.content += '#include <dlfcn.h>\n'
    #self.content += '#include <iostream>\n'
    self.content += '#include \"roctracer_kfd.h\"\n'
    self.content += '#include \"hsakmt.h\"\n'

    self.content += '#define PUBLIC_API __attribute__((visibility(\"default\")))\n'

    self.add_section('API ID enumeration', '  ', self.gen_id_enum)
    self.add_section('API arg structure', '    ', self.gen_arg_struct)

    self.content += '\n'
    self.content += '#if PROF_API_IMPL\n'
    self.content += 'namespace roctracer {\n'
    self.content += 'namespace kfd_support {\n'

    self.add_section('API intercepting code', '', self.gen_intercept_decl)
    self.add_section('API intercepting code', '', self.gen_intercept)
    self.add_section('API callback functions', '', self.gen_callbacks)

    self.add_section('API get_name function', '    ', self.gen_get_name)
    self.add_section('API get_code function', '  ', self.gen_get_code)
    self.content += '\n};};\n'
    self.content += '#endif // PROF_API_IMPL\n'

    self.content += '#endif // ' + out_macro + 'H_'

    self.content_cpp += "// automatically generated\n\n" + license + '\n'
    self.content_cpp += "/////////////////////////////////////////////////////////////////////////////\n\n"
    self.content_cpp += '#include \"kfd_prof_str.h\"\n'

    self.add_section_h('API output stream', '    ', self.gen_out_stream)
    self.add_section_h('API output stream', '    ', self.gen_public_api)

    self.content_cpp += '}\n'

    self.content_cpp += '\n'

  # add code section
  def add_section(self, title, gap, fun):
    n = 0
    self.content +=  '\n// section: ' + title + '\n\n'
    fun(-1, '-', '-', {})
    for index in range(len(self.api_names)):
      last = (index == len(self.api_names) - 1)
      name = self.api_names[index]
      print ("API", name)

      if n != 0:
        if gap == '': fun(n, name, '-', {})
        self.content += '\n'
      self.content += gap + '// block: ' + name + ' API\n'
      for call in self.api_calls[name]:
        fun(n, name, call, self.api_data[call])
        n += 1
    fun(n, '-', '-', {})


  def add_section_h(self, title, gap, fun):
    n = 0
    self.content_cpp +=  '\n// section: ' + title + '\n\n'
    fun(-1, '-', '-', {})
    for index in range(len(self.api_names)):
      last = (index == len(self.api_names) - 1)
      name = self.api_names[index]
      print ("API", name)

      if n != 0:
        if gap == '': fun(n, name, '-', {})
        self.content_cpp += '\n'
      self.content_cpp += gap + '// block: ' + name + ' API\n'
      for call in self.api_calls[name]:
        fun(n, name, call, self.api_data[call])
        n += 1
    fun(n, '-', '-', {})

  # generate API ID enumeration
  def gen_id_enum(self, n, name, call, data):
    if n == -1:
      self.content += 'enum kfd_api_id_t {\n'
      return
    if call != '-':
      self.content += '  ' + self.api_id[call] + ' = ' + str(n) + ',\n'
    else:
      self.content += '\n'
      self.content += '  KFD_API_ID_NUMBER = ' + str(n) + ',\n'
      self.content += '  KFD_API_ID_ANY = ' + str(n + 1) + ',\n'
      self.content += '};\n'
    
  def is_arr(self, record):
    return re.match(r'\s*(.*)\s+(.*)\[\]\s*', record)

  # generate API args structure
  def gen_arg_struct(self, n, name, call, struct):
    if n == -1:
      self.content += 'struct kfd_api_data_t {\n'
      self.content += '  uint64_t correlation_id;\n'
      self.content += '  uint32_t phase;\n'
      self.content += '  union {\n'
      for ret_type in self.api_rettypes:
        self.content += '    ' + ret_type + ' ' + ret_type + '_retval;\n'
      self.content += '  };\n'
      self.content += '  union {\n'
      return
    if call != '-':
      self.content +=   '    struct {\n'
      for (var, item) in struct['astr'].items():
        m = self.is_arr(item)
        if m:
          self.content += '      ' + m.group(1) +'* '+ m.group(2)+';\n'
        else:
          self.content += '      ' + item + ';\n'
      self.content +=   '    } '+ call + ';\n'
    else:
      self.content += '  } args;\n'
      self.content += '};\n'
    
  # generate API callbacks
  def gen_callbacks(self, n, name, call, struct):
    if n == -1:
      self.content += 'typedef CbTable<KFD_API_ID_NUMBER> cb_table_t;\n'
      self.content += 'cb_table_t cb_table;\n'
      self.content += '\n'
    if call != '-':
      call_id = self.api_id[call];
      ret_type = struct['ret']
      self.content += ret_type + ' ' + call + '_callback(' + struct['args'] + ') {\n'  # 'static ' +
      if call == 'hsaKmtOpenKFD':
        self.content += '  if (' + name + '_saved == NULL) intercept_KFDApiTable();\n'
      self.content += '  kfd_api_data_t api_data{};\n'
      for var in struct['alst']:
        self.content += '  api_data.args.' + call + '.' + var.replace("[]","") + ' = ' + var.replace("[]","") + ';\n'
      self.content += '  activity_rtapi_callback_t api_callback_fun = NULL;\n'
      self.content += '  void* api_callback_arg = NULL;\n'
      self.content += '  cb_table.get(' + call_id + ', &api_callback_fun, &api_callback_arg);\n'
      self.content += '  api_data.phase = 0;\n'
      self.content += '  if (api_callback_fun) api_callback_fun(ACTIVITY_DOMAIN_KFD_API, ' + call_id + ', &api_data, api_callback_arg);\n'
      if ret_type != 'void':
        self.content += '  ' + ret_type + ' ret ='
      tmp_str = '  ' + name + '_saved->' + call + '_fn(' + ', '.join(struct['alst']) + ');\n'
      self.content += tmp_str.replace("[]","")
      if ret_type != 'void':
        self.content += '  api_data.' + ret_type + '_retval = ret;\n'
      self.content += '  api_data.phase = 1;\n'
      self.content += '  if (api_callback_fun) api_callback_fun(ACTIVITY_DOMAIN_KFD_API, ' + call_id + ', &api_data, api_callback_arg);\n'
      if ret_type != 'void':
        self.content += '  return ret;\n'
      self.content += '}\n'

  def gen_intercept_decl(self, n, name, call, struct):
    if n > 0 and call == '-':
      self.content += '} HSAKMTAPI_saved_t;\n'
    if n == 0 or (call == '-' and name != '-'):
      self.content += 'typedef struct {\n'
    if call != '-':
      if call != 'hsa_shut_down':
        self.content += '  decltype(' + call + ')* ' + call + '_fn;\n'
      else: # Unused
        self.content += '  { void* p = (void*)' + call + '_callback; (void)p; }\n'

  # generate API intercepting code
  def gen_intercept(self, n, name, call, struct):
    if n > 0 and call == '-':
      self.content += '};\n'
    if n == 0 or (call == '-' and name != '-'):
      self.content += name + '_saved_t* ' + name + '_saved = NULL;\n'
      self.content += 'void intercept_' + 'KFDApiTable' + '(void) {\n'
      self.content += '  ' + name + '_saved = new ' + name + '_saved_t{}' + ';\n'

    if call != '-':
      if call != 'hsa_shut_down':
        self.content += '  typedef decltype(' + name + '_saved_t::' + call + '_fn) ' + call + '_t;\n'
        self.content += '  ' + name + '_saved->' + call + '_fn = (' + call + '_t)' + 'dlsym(RTLD_NEXT,\"'  + call + '\");\n' 
      else: 
        self.content += '  { void* p = (void*)' + call + '_callback; (void)p; }\n'

  # generate API name function
  def gen_get_name(self, n, name, call, struct):
    if n == -1:
      self.content += 'static const char* GetApiName(const uint32_t& id) {\n'
      self.content += '  switch (id) {\n'
      return
    if call != '-':
      self.content += '    case ' + self.api_id[call] + ': return "' + call + '";\n'
    else:
      self.content += '  }\n'
      self.content += '  return "unknown";\n'
      self.content += '}\n'

  # generate API code function
  def gen_get_code(self, n, name, call, struct):
    if n == -1:
      self.content += 'static uint32_t GetApiCode(const char* str) {\n'
      return
    if call != '-':
      self.content += '  if (strcmp("' + call + '", str) == 0) return ' + self.api_id[call] + ';\n'
    else:
      self.content += '  return KFD_API_ID_NUMBER;\n'
      self.content += '}\n'

  # generate stream operator
  def gen_out_stream(self, n, name, call, struct):
    if n == -1:
      self.content_cpp += 'typedef std::pair<uint32_t, kfd_api_data_t> kfd_api_data_pair_t;\n'
      self.content_cpp += 'inline std::ostream& operator<< (std::ostream& out, const hsa_api_data_pair_t& data_pair) {\n'
      self.content_cpp += '  const uint32_t cid = data_pair.first;\n'
      self.content_cpp += '  const kfd_api_data_t& api_data = data_pair.second;\n'
      self.content_cpp += '  switch(cid) {\n'
      return
    if call != '-':
      self.content_cpp += '    case ' + self.api_id[call] + ': {\n'
      self.content_cpp += '      out << "' + call + '(";\n'
      arg_list = struct['alst']
      if len(arg_list) != 0:
        for ind in range(len(arg_list)):
          arg_var = arg_list[ind]
          arg_val = 'api_data.args.' + call + '.' + arg_var
          self.content_cpp += '      typedef decltype(' + arg_val.replace("[]","") + ') arg_val_type_t' + str(ind) + ';\n'
          self.content_cpp += '      roctracer::kfd_support::output_streamer<arg_val_type_t' + str(ind) + '>::put(out, ' + arg_val.replace("[]","") + ')'
          '''
          arg_item = struct['tlst'][ind]
          if re.search(r'\(\* ', arg_item): arg_pref = ''
          elif re.search(r'void\* ', arg_item): arg_pref = ''
          elif re.search(r'\*\* ', arg_item): arg_pref = '**'
          elif re.search(r'\* ', arg_item): arg_pref = '*'
          else: arg_pref = ''
          if arg_pref != '':
            self.content += '      if (' + arg_val + ') out << ' + arg_pref + '(' + arg_val + '); else out << ' + arg_val
          else:
            self.content += '      out << ' + arg_val
          '''
          if ind < len(arg_list) - 1: self.content_cpp += ' << ", ";\n'
          else: self.content_cpp += ';\n'
      if struct['ret'] != 'void':
        self.content_cpp += '      out << ") = " << api_data.' + struct['ret'] + '_retval;\n'
      else:
        self.content_cpp += '      out << ") = void";\n'
      self.content_cpp += '      break;\n'
      self.content_cpp += '    }\n'
    else:
      self.content_cpp += '    default:\n'
      self.content_cpp += '      out << "ERROR: unknown API";\n'
      self.content_cpp += '      abort();\n'
      self.content_cpp += '  }\n'
      self.content_cpp += '  return out;\n'
      self.content_cpp += '}\n'
      self.content_cpp += 'inline std::ostream& operator<< (std::ostream& out, const HsaMemFlags& v) { out << "HsaMemFlags"; return out; }\n' 



  def gen_public_api(self, n, name, call, struct):
    if n == -1:
      self.content_cpp += 'extern "C" {\n'
    if call != '-':
      self.content_cpp += 'PUBLIC_API HSAKMT_STATUS ' + call + '(' + struct['args'] + ') { roctracer::kfd_support::' + call + '_callback('
      for i in range(0,len(struct['alst'])):
        if i == (len(struct['alst'])-1):
          self.content_cpp += struct['alst'][i].replace("[]","") 
        else:
          self.content_cpp += struct['alst'][i].replace("[]","") + ', '
      self.content_cpp +=  ');} \n'

#############################################################
# main
# Usage
if len(sys.argv) != 3:
  print >>sys.stderr, "Usage:", sys.argv[0], " <rocTracer root> <KFD include path>"
  sys.exit(1)
else:
  ROOT = sys.argv[1] + '/'
  KFD_DIR = sys.argv[2] + '/'

descr = API_DescrParser(OUT, KFD_DIR, API_TABLES_H, API_HEADERS_H, LICENSE)

out_file = ROOT + OUT + '.h'
print 'Generating "' + out_file + '"'
f = open(out_file, 'w')
f.write(descr.content[:-1])
f.close()

out_file = ROOT + OUT_CPP + '.cpp'
print 'Generating "' + out_file + '"'
f = open(out_file, 'w')
f.write(descr.content_cpp[:-1])
f.close()

#############################################################