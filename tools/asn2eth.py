#!/usr/bin/env python

#
# competh.py
# ASN.1 to Ethereal dissector compiler
# 2004 Tomas Kukosa 
#
# $Id$
#

"""ASN.1 to Ethereal dissector compiler"""

#
# Compiler from ASN.1 specification to the Ethereal dissector
#
# Based on ASN.1 to Python compiler from Aaron S. Lav's PyZ3950 package licensed under the X Consortium license
# http://www.pobox.com/~asl2/software/PyZ3950/
# (ASN.1 to Python compiler functionality is broken but not removed, it could be revived if necessary)
#
# It requires Dave Beazley's PLY parsing package licensed under the LGPL (tested with version 1.3.1)
# http://systems.cs.uchicago.edu/ply/
# 
# 
# ITU-T Recommendation X.680 (07/2002), 
#   Information technology - Abstract Syntax Notation One (ASN.1): Specification of basic notation
#
# ITU-T Recommendation X.682 (07/2002), 
#   Information technology - Abstract Syntax Notation One (ASN.1): Constraint specification
#
# ITU-T Recommendation X.683 (07/2002), 
#   Information technology - Abstract Syntax Notation One (ASN.1): Parameterization of ASN.1 specifications
#

from __future__ import nested_scopes

import warnings

# OID name -> number conversion table
oid_names = {
  '/itu-t' : 0,
  '0/recommendation' : 0,
  '0.0/h' : 8,
  '0.0/q' : 17,
  '0.0/x' : 24,
  '0/question' : 1,
  '0/administration' : 2,
  '0/network-operator' : 3,
  '0/identified-organization' : 4,
  '0/r-recommendation' : 5,
  '0/data' : 9,
  '/iso' : 1,
  '1/standard' : 0,
  '1/registration-authority' : 1,
  '1/member-body' : 2,
  '1/identified-organization' : 3,
  '/joint-iso-itu-t' : 2,
  '2/presentation' : 0,
  '2/asn1' : 1,
  '2/association-control' : 2,
  '2/reliable-transfer' : 3,
  '2/remote-operations' : 4,
  '2/ds' : 5,
  '2/mhs' : 6,
  '2/ccr' : 7,
  '2/oda' : 8,
  '2/ms' : 9,
}

class LexError(Exception): pass
class ParseError(Exception): pass

# 11 ASN.1 lexical items

static_tokens = {
  r'::='    : 'ASSIGNMENT',  # 11.16 Assignment lexical item
  r'\.\.'   : 'RANGE',       # 11.17 Range separator
  r'\.\.\.' : 'ELLIPSIS',    # 11.18 Ellipsis
  #r'\[\['   : 'LVERBRACK',   # 11.19 Left version brackets
  #r'\]\]'   : 'RVERBRACK',   # 11.20 Right version brackets
  # 11.26 Single character lexical items
  r'\{' : 'LBRACE',
  r'\}' : 'RBRACE',
  r'<'  : 'LT',
  #r'>'  : 'GT',
  r','  : 'COMMA',
  r'\.' : 'DOT',
  r'\(' : 'LPAREN',
  r'\)' : 'RPAREN',
  r'\[' : 'LBRACK',
  r'\]' : 'RBRACK',
  r'-'  : 'MINUS',
  r':'  : 'COLON',
  #r'='  : 'EQ',
  #r'"'  : 'QUOTATION',
  #r"'"  : 'APOSTROPHE',
  r';'  : 'SEMICOLON',
  #r'@'  : 'AT',
  #r'\!' : 'EXCLAMATION',
  #r'\^' : 'CIRCUMFLEX'
}

# 11.27 Reserved words

# all keys in reserved_words must start w/ upper case
reserved_words = {
    'TAGS' : 'TAGS',
    'BOOLEAN' : 'BOOLEAN',
    'INTEGER' : 'INTEGER',
    'BIT'     : 'BIT',
    'CHARACTER' : 'CHARACTER',
    'STRING'  : 'STRING',
    'OCTET'   : 'OCTET',
    'NULL'    : 'NULL',
    'SEQUENCE': 'SEQUENCE',
    'OF'      : 'OF',
    'SET'     : 'SET',
    'IMPLICIT': 'IMPLICIT',
    'CHOICE'  : 'CHOICE',
    'ANY'     : 'ANY',
#    'EXTERNAL' : 'EXTERNAL', # XXX added over base
    'OPTIONAL':'OPTIONAL',
    'DEFAULT' : 'DEFAULT',
    'COMPONENTS': 'COMPONENTS',
    'UNIVERSAL' : 'UNIVERSAL',
    'APPLICATION' : 'APPLICATION',
    'PRIVATE'   : 'PRIVATE',
    'TRUE' : 'TRUE',
    'FALSE' : 'FALSE',
    'BEGIN' : 'BEGIN',
    'END' : 'END',
    'DEFINITIONS' : 'DEFINITIONS',
    'EXPLICIT' : 'EXPLICIT',
    'ENUMERATED' : 'ENUMERATED',
    'EXPORTS' : 'EXPORTS',
    'IMPORTS' : 'IMPORTS',
    'REAL'    : 'REAL',
    'INCLUDES': 'INCLUDES',
    'MIN'     : 'MIN',
    'MAX'     : 'MAX',
    'SIZE'    : 'SIZE',
    'FROM'    : 'FROM',
    'PATTERN'    : 'PATTERN',
    'WITH'    : 'WITH',
    'COMPONENT': 'COMPONENT',
    'PRESENT'  : 'PRESENT',
    'ABSENT'   : 'ABSENT',
    'DEFINED'  : 'DEFINED',
    'CONSTRAINED' : 'CONSTRAINED',
    'BY'       : 'BY',
    'PLUS-INFINITY'   : 'PLUS_INFINITY',
    'MINUS-INFINITY'  : 'MINUS_INFINITY',
    'GeneralizedTime' : 'GeneralizedTime',
    'UTCTime'         : 'UTCTime',
    'ObjectDescriptor': 'ObjectDescriptor',
    'AUTOMATIC': 'AUTOMATIC',
    'OBJECT': 'OBJECT',
    'IDENTIFIER': 'IDENTIFIER',
#      'OPERATION'       : 'OPERATION',
#      'ARGUMENT'        : 'ARGUMENT',
#      'RESULT'          : 'RESULT',
#      'ERRORS'          : 'ERRORS',
#      'LINKED'          : 'LINKED',
#      'ERROR'           : 'ERROR',
#      'PARAMETER'       : 'PARAMETER',
#      'BIND'            : 'BIND',
#      'BIND-ERROR'      : 'BIND_ERROR',
#      'UNBIND'          : 'UNBIND',
#      'APPLICATION-CONTEXT' : 'AC',
#      'APPLICATON-SERVICE-ELEMENTS' : 'ASES',
#      'REMOTE' : 'REMOTE',
#      'INITIATOR' : 'INITIATOR',
#      'RESPONDER' : 'RESPONDER',
#      'APPLICATION-SERVICE-ELEMENT' : 'ASE',
#      'OPERATIONS' : None,
#      'EXTENSION-ATTRIBUTE' : 'EXTENSION_ATTRIBUTE',
#      'EXTENSIONS' : None,
#      'CHOSEN' : None,
#      'EXTENSION' : None,
#      'CRITICAL': None,
#      'FOR' : None,
#      'SUBMISSION' : None,
#      'DELIVERY' : None,
#      'TRANSFER' : None,
#      'OBJECT' : None,
#      'PORTS' : None,
#      'PORT'  : None,
#      r'ABSTRACT\s*OPERATIONS' : 'ABSTR_OPS',
#      'REFINE' : None,
#      'AS' : None,
#      'RECURRING' : None
    }

for k in static_tokens.keys ():
    if static_tokens [k] == None:
        static_tokens [k] = k

StringTypes = ['Numeric', 'Printable', 'IA5', 'BMP', 'Universal', 'UTF8',
               'Teletex', 'T61', 'Videotex', 'Graphic', 'ISO646', 'Visible',
               'General']

for s in StringTypes:
  reserved_words[s + 'String'] = s + 'String'

tokens = static_tokens.values() \
         + reserved_words.values() \
         + ['BSTRING', 'HSTRING', 'QSTRING',
            'UCASE_IDENT', 'LCASE_IDENT',
            'NUMBER', 'PYQUOTE']

import __main__ # XXX blech!

for (k, v) in static_tokens.items ():
  __main__.__dict__['t_' + v] = k

# 11.10 Binary strings
def t_BSTRING (t):
    r"'[01]*'B"
    return t

# 11.12 Hexadecimal strings
def t_HSTRING (t):
    r"'[0-9A-Fa-f]*'H"
    return t

def t_QSTRING (t):
    r'"([^"]|"")*"'
    return t # XXX might want to un-""

def t_UCASE_IDENT (t):
    r"[A-Z](-[a-zA-Z0-9]|[a-zA-Z0-9])*" # can't end w/ '-'
    t.type = reserved_words.get(t.value, "UCASE_IDENT")
    #t.value = t.value.replace('-', '_') # XXX is it OK to do this during lex
    return t

def t_LCASE_IDENT (t):
    r"[a-z](-[a-zA-Z0-9]|[a-zA-Z0-9])*" # can't end w/ '-'
    #t.value = t.value.replace ('-', '_')  # XXX is it OK to do this during lex
    return t

# 11.8 Numbers
def t_NUMBER (t):
    r"0|([1-9][0-9]*)"
    return t

# 11.9 Real numbers
# not supported yet

# 11.6 Comments
pyquote_str = 'PYQUOTE'
def t_COMMENT(t):
    r"--(-[^\-\n]|[^\-\n])*(--|\n|-\n|$|-$)"
    if (t.value.find("\n") >= 0) : t.lineno += 1
    if t.value[2:2+len (pyquote_str)] == pyquote_str:
        t.value = t.value[2+len(pyquote_str):]
        t.value = t.value.lstrip ()
        t.type = pyquote_str
        return t
    return None

t_ignore = " \t\r"

def t_NEWLINE(t):
    r'\n+'
    t.lineno += t.value.count("\n")

def t_error(t):
    print "Error", t.value[:100], t.lineno
    raise LexError

    
import lex
lexer = lex.lex(debug=0)

import yacc

class Ctx:
    def __init__ (self, defined_dict, indent = 0):
        self.tags_def = 'EXPLICIT' # default = explicit
        self.indent_lev = 0
        self.assignments = {}
        self.dependencies = {}
        self.pyquotes = []
        self.defined_dict = defined_dict
        self.name_ctr = 0
    def spaces (self):
        return " " * (4 * self.indent_lev)
    def indent (self):
        self.indent_lev += 1
    def outdent (self):
        self.indent_lev -= 1
        assert (self.indent_lev >= 0)
    def register_assignment (self, ident, val, dependencies):
        if self.assignments.has_key (ident):
            raise "Duplicate assignment for " + ident
        if self.defined_dict.has_key (ident):
            raise "cross-module duplicates for " + ident
        self.defined_dict [ident] = 1
        self.assignments[ident] = val
        self.dependencies [ident] = dependencies
        return ""
    #        return "#%s depends on %s" % (ident, str (dependencies))
    def register_pyquote (self, val):
        self.pyquotes.append (val)
        return ""
    def output_assignments (self):
        already_output = {}
        text_list = []
        assign_keys = self.assignments.keys()
        to_output_count = len (assign_keys)
        while 1:
            any_output = 0
            for (ident, val) in self.assignments.iteritems ():
                if already_output.has_key (ident):
                    continue
                ok = 1
                for d in self.dependencies [ident]:
                    if (not already_output.has_key (d) and
                        d in assign_keys):
                        ok = 0
                if ok:
                    text_list.append ("%s=%s" % (ident,
                                                self.assignments [ident]))
                    already_output [ident] = 1
                    any_output = 1
                    to_output_count -= 1
                    assert (to_output_count >= 0)
            if not any_output:
                if to_output_count == 0:
                    break
                # OK, we detected a cycle
                cycle_list = []
                for ident in self.assignments.iterkeys ():
                    if not already_output.has_key (ident):
                        depend_list = [d for d in self.dependencies[ident] if d in assign_keys]
                        cycle_list.append ("%s(%s)" % (ident, ",".join (depend_list)))
                        
                text_list.append ("# Cycle XXX " + ",".join (cycle_list))
                for (ident, val) in self.assignments.iteritems ():
                    if not already_output.has_key (ident):
                        text_list.append ("%s=%s" % (ident, self.assignments [ident]))
                break

        return "\n".join (text_list)
    def output_pyquotes (self):
        return "\n".join (self.pyquotes)
    def make_new_name (self):
        self.name_ctr += 1
        return "_compiler_generated_name_%d" % (self.name_ctr,)

#--- EthCtx -------------------------------------------------------------------
class EthCtx:
  def __init__(self, conform, indent = 0):
    self.tags_def = 'EXPLICIT' # default = explicit
    self.conform = conform
    self.assign = {}
    self.assign_ord = []
    self.field = {}
    self.field_ord = []
    self.type = {}
    self.type_ord = []
    self.type_imp = []
    self.type_dep = {}
    self.vassign = {}
    self.vassign_ord = []
    self.value = {}
    self.value_ord = []
    self.value_imp = []

  def pvp(self):  # PER dissector version postfix
    if (self.new):
      return '_new'
    else:
      return ''

  # API type
  def Org(self): return not self.new
  def New(self): return self.new
  def Per(self): return self.encoding == 'per'
  def OPer(self): return self.Org() and self.Per()
  def NPer(self): return self.New() and self.Per()
  def Ber(self): return self.encoding == 'ber'
  def OBer(self): return self.Org() and self.Ber()
  def NBer(self): return self.New() and self.Ber()

  def dbg(self, d):
    if (self.dbgopt.find(d) >= 0):
      return True
    else:
      return False

  def eth_get_type_attr(self, type):
    types = [type]
    while (not self.type[type]['import'] 
           and self.type[type]['val'].type == 'Type_Ref'):
      type = self.type[type]['val'].val
      types.append(type)
    attr = {}
    while len(types):
      t = types.pop()
      attr.update(self.type[t]['attr'])
      attr.update(self.eth_type[self.type[t]['ethname']]['attr'])
    return attr

  #--- eth_reg_assign ---------------------------------------------------------
  def eth_reg_assign(self, ident, val):
    #print "eth_reg_assign(ident='%s')" % (ident)
    if self.assign.has_key(ident):
      raise "Duplicate assignment for " + ident
    self.assign[ident] = val
    self.assign_ord.append(ident)

  #--- eth_reg_vassign --------------------------------------------------------
  def eth_reg_vassign(self, vassign):
    ident = vassign.ident
    #print "eth_reg_vassign(ident='%s')" % (ident)
    if self.vassign.has_key(ident):
      raise "Duplicate value assignment for " + ident
    self.vassign[ident] = vassign
    self.vassign_ord.append(ident)

  #--- eth_import_type --------------------------------------------------------
  def eth_import_type(self, ident, mod, proto):
    #print "eth_import_type(ident='%s', mod='%s', prot='%s')" % (ident, mod, prot)
    if self.type.has_key(ident):
      raise "Duplicate type for " + ident
    self.type[ident] = {'import'  : mod, 'proto' : proto,
                        'ethname' : '' }
    self.type[ident]['attr'] = { 'TYPE' : 'FT_NONE', 'DISPLAY' : 'BASE_NONE',
                                 'STRINGS' : 'NULL', 'BITMASK' : '0' }
    self.type[ident]['attr'].update(self.conform.use_item('TYPE_ATTR', ident))
    self.type_imp.append(ident)

  #--- eth_import_value -------------------------------------------------------
  def eth_import_value(self, ident, mod, proto):
    #print "eth_import_value(ident='%s', mod='%s', prot='%s')" % (ident, mod, prot)
    if self.type.has_key(ident):
      raise "Duplicate value for " + ident
    self.value[ident] = {'import'  : mod, 'proto' : proto,
                         'ethname' : ''}
    self.value_imp.append(ident)

  #--- eth_dep_add ------------------------------------------------------------
  def eth_dep_add(self, type, dep):
    if self.type_dep.has_key(type):
      self.type_dep[type].append(dep)
    else:
      self.type_dep[type] = [dep]

  #--- eth_reg_type -----------------------------------------------------------
  def eth_reg_type(self, ident, val):
    #print "eth_reg_type(ident='%s')" % (ident)
    if self.type.has_key(ident):
      raise "Duplicate type for " + ident
    self.type[ident] = { 'val' : val, 'import' : None }
    if len(ident.split('/')) > 1:
      self.type[ident]['tname'] = val.eth_tname()
    else:
      self.type[ident]['tname'] = ident.replace('-', '_')
    self.type[ident]['export'] = self.conform.use_item('EXPORTS', ident)
    self.type[ident]['user_def'] = self.conform.use_item('USER_DEFINED', ident)
    self.type[ident]['no_emit'] = self.conform.use_item('NO_EMIT', ident)
    self.type[ident]['tname'] = self.conform.use_item('TYPE_RENAME', ident, val_dflt=self.type[ident]['tname'])
    self.type[ident]['ethname'] = ''
    if val.type == 'Type_Ref':
      self.type[ident]['attr'] = {}
    else:
      (ftype, display) = val.eth_ftype()
      self.type[ident]['attr'] = { 'TYPE' : ftype, 'DISPLAY' : display,
                                   'STRINGS' : val.eth_strings(), 'BITMASK' : '0' }
    self.type[ident]['attr'].update(self.conform.use_item('TYPE_ATTR', ident))
    self.type_ord.append(ident)

  #--- eth_reg_value ----------------------------------------------------------
  def eth_reg_value(self, ident, type, value):
    #print "eth_reg_value(ident='%s')" % (ident)
    if self.value.has_key(ident):
      raise "Duplicate value for " + ident
    self.value[ident] = { 'type' : type, 'value' : value, 'import' : None }
    self.value[ident]['export'] = self.conform.use_item('EXPORTS', ident)
    self.value[ident]['ethname'] = ''
    self.value_ord.append(ident)

  #--- eth_reg_field ----------------------------------------------------------
  def eth_reg_field(self, ident, type, idx='', parent=None, impl=False):
    #print "eth_reg_field(ident='%s', type='%s')" % (ident, type)
    if self.field.has_key(ident):
      raise "Duplicate field for " + ident
    self.field[ident] = {'type' : type, 'idx' : idx, 'impl' : impl, 
                         'modified' : '', 'attr' : {} }
    if self.conform.check_item('FIELD_ATTR', ident):
      self.field[ident]['modified'] = '#' + str(id(self))
      self.field[ident]['attr'].update(self.conform.use_item('FIELD_ATTR', ident))
    self.field_ord.append(ident)
    if parent: self.eth_dep_add(parent, type)

  #--- eth_prepare ------------------------------------------------------------
  def eth_prepare(self):
    #--- types -------------------
    self.eth_type = {}
    self.eth_type_ord = []
    self.eth_export_ord = []
    self.eth_type_dupl = {}
    self.named_bit = []

    for t in self.type_imp:
      nm = t
      self.eth_type[nm] = { 'import' : self.type[t]['import'], 'proto' : self.type[t]['proto'],
                            'attr' : {}, 'ref' : []}
      self.type[t]['ethname'] = nm
    for t in self.type_ord:
      nm = self.type[t]['tname']
      if ((nm.find('#') >= 0) or 
          ((len(t.split('/'))>1) and self.conform.get_fn_presence(t) and not self.conform.check_item('TYPE_RENAME', t))):
        if len(t.split('/')) == 2 and t.split('/')[1] == '_item':  # Sequnce of type at the 1st level
          nm = t.split('/')[0] + t.split('/')[1]
        elif t.split('/')[-1] == '_item':  # Sequnce of type at next levels
          nm = 'T_' + t.split('/')[-2] + t.split('/')[-1]
        else:
          nm = 'T_' + t.split('/')[-1]
        nm = nm.replace('-', '_')
        if self.eth_type.has_key(nm):
          if self.eth_type_dupl.has_key(nm):
            self.eth_type_dupl[nm].append(t)
          else:
            self.eth_type_dupl[nm] = [self.eth_type[nm]['ref'][0], t]
          nm += str(len(self.eth_type_dupl[nm])-1)
      if self.eth_type.has_key(nm):
        self.eth_type[nm]['ref'].append(t)
      else:
        self.eth_type_ord.append(nm)
        self.eth_type[nm] = { 'import' : None, 'proto' : self.proto, 'export' : 0,
                              'user_def' : 0x03, 'no_emit' : 0x03, 
                              'val' : self.type[t]['val'], 
                              'attr' : {}, 
                              'ref' : [t]}
        self.eth_type[nm]['attr'].update(self.conform.use_item('ETYPE_ATTR', nm))
        if self.type[t]['attr'].get('STRINGS') == '$$':
          self.eth_type[nm]['attr']['STRINGS'] = 'VALS(%s_vals)' % (nm)
      self.type[t]['ethname'] = nm
      if (not self.eth_type[nm]['export'] and self.type[t]['export']):  # new export
        self.eth_export_ord.append(nm)
      self.eth_type[nm]['export'] |= self.type[t]['export']
      self.eth_type[nm]['user_def'] &= self.type[t]['user_def']
      self.eth_type[nm]['no_emit'] &= self.type[t]['no_emit']
    for t in self.eth_type_ord:
      bits = self.eth_type[t]['val'].eth_named_bits()
      if (bits):
        for (val, id) in bits:
          self.named_bit.append({'name' : id, 'val' : val,
                                 'ethname' : 'hf_%s_%s_%s' % (self.proto, t, id),
                                 'ftype'   : 'FT_BOOLEAN', 'display' : '8',
                                 'strings' : 'NULL',
                                 'bitmask' : '0x'+('80','40','20','10','08','04','02','01')[val%8]})
      if self.eth_type[t]['val'].eth_need_tree():
        self.eth_type[t]['tree'] = "ett_%s_%s" % (self.proto, t)
      else:
        self.eth_type[t]['tree'] = None

    #--- value dependencies -------------------
    self.value_dep = {}
    for v in self.value_ord:
      if isinstance (self.value[v]['value'], Value):
        dep = self.value[v]['value'].get_dep()
      else:
        dep = self.value[v]['value']
      if dep and self.value.has_key(dep):
        if self.value_dep.has_key(v):
          self.value_dep[v].append(dep)
        else:
          self.value_dep[v] = [dep]
    
    for v in self.value_ord:
      if not self.value[v]['export']: continue
      deparr = self.value_dep.get(v, [])
      while deparr:
        d = deparr.pop()
        if not self.value[d]['import']:
          if not self.value[d]['export']:
            self.value[d]['export'] = 0x01
            deparr.extend(self.value_dep.get(d, []))

    #--- values -------------------
    self.eth_value = {}
    self.eth_value_ord = []

    for v in self.value_imp:
      nm = v.replace('-', '_')
      self.eth_value[nm] = { 'import' : self.value[v]['import'], 'proto' : self.value[v]['proto'], 'ref' : []}
      self.value[v]['ethname'] = nm
    for v in self.value_ord:
      nm = v.replace('-', '_')
      self.eth_value[nm] = { 'import' : None, 'proto' : self.proto, 
                             'export' : self.value[v]['export'], 'ref' : [v] }
      if isinstance (self.value[v]['value'], Value):
        self.eth_value[nm]['value'] = self.value[v]['value'].to_str()
        dep = self.value[v]['value'].get_dep()
      else:
        self.eth_value[nm]['value'] = self.value[v]['value']
        dep = self.value[v]['value']
      if dep and self.value.has_key(dep):
        if self.value_dep.has_key(v):
          self.value_dep[v].append(dep)
        else:
          self.value_dep[v] = [dep]
      self.eth_value_ord.append(nm)
      self.value[v]['ethname'] = nm

    #--- fields -------------------------
    self.eth_hf = {}
    self.eth_hf_ord = []
    self.eth_hf_dupl = {}

    for f in self.field_ord:
      if len(f.split('/')) > 1 and f.split('/')[-1] == '_item':  # Sequnce of type
        nm = f.split('/')[-2] + f.split('/')[-1]
        name = 'Item'
      else:
        nm = f.split('/')[-1]
        name = nm
      name += self.field[f]['idx']
      abbrev = nm.replace('-', '_')
      nm = self.conform.use_item('FIELD_RENAME', f, val_dflt=nm)
      nm = nm.replace('-', '_')
      t = self.field[f]['type']
      if self.type.has_key(t):
        ethtype = self.type[t]['ethname']
      else:  # undefined type
        # dummy imported
        print "Dummy imported: ", t
        self.type[t] = {'import'  : 'xxx', 'proto' : 'xxx',
                        'ethname' : t }
        self.type[t]['attr'] = { 'TYPE' : 'FT_NONE', 'DISPLAY' : 'BASE_NONE',
                                 'STRINGS' : 'NULL', 'BITMASK' : '0' }
        self.eth_type[t] = { 'import' : 'xxx', 'proto' : 'xxx' , 'attr' : {}, 'ref' : []}
        ethtype = t
      ethtypemod = ethtype + self.field[f]['modified']
      if self.eth_hf.has_key(nm):
        if self.eth_hf_dupl.has_key(nm):
          if self.eth_hf_dupl[nm].has_key(ethtypemod):
            nm = self.eth_hf_dupl[nm][ethtypemod]
            self.eth_hf[nm]['ref'].append(f)
            self.field[f]['ethname'] = nm
            continue
          else:
            nmx = nm + str(len(self.eth_hf_dupl[nm]))
            self.eth_hf_dupl[nm][ethtype] = nmx
            nm = nmx
        else:
          if (self.eth_hf[nm]['ethtype']+self.eth_hf[nm]['modified']) == ethtypemod:
            self.eth_hf[nm]['ref'].append(f)
            self.field[f]['ethname'] = nm
            continue
          else:
            self.eth_hf_dupl[nm] = {self.eth_hf[nm]['ethtype']+self.eth_hf[nm]['modified'] : nm, \
                                    ethtypemod : nm+'1'}
            nm += '1'
      self.eth_hf_ord.append(nm)
      fullname = "hf_%s_%s" % (self.proto, nm)
      attr = self.eth_get_type_attr(self.field[f]['type']).copy()
      attr.update(self.field[f]['attr'])
      attr['NAME'] = '"%s"' % name
      attr['ABBREV'] = abbrev
      attr.update(self.conform.use_item('EFIELD_ATTR', nm))
      self.eth_hf[nm] = {'fullname' : fullname,
                         'ethtype' : ethtype, 'modified' : self.field[f]['modified'],
                         'attr' : attr.copy(), 'ref' : [f]}
      self.field[f]['ethname'] = nm
    #--- type dependencies -------------------
    self.eth_type_ord1 = []
    self.eth_dep_cycle = []
    self.dep_cycle_eth_type = {}
    x = {}  # already emitted
    #print '# Dependency computation'
    for t in self.type_ord:
      if x.has_key(self.type[t]['ethname']):
        continue
      stack = [t]
      stackx = {t : self.type_dep.get(t, [])[:]}
      #print 'Push: %s : %s' % (t, str(stackx[t]))
      while stack:
        if stackx[stack[-1]]:  # has dependencies
          d = stackx[stack[-1]].pop(0)
          if x.has_key(self.type[d]['ethname']) or self.type[d]['import']:
            continue
          if stackx.has_key(d):  # cyclic dependency
            c = stack[:]
            c.reverse()
            c = [d] + c[0:c.index(d)+1]
            c.reverse()
            self.eth_dep_cycle.append(c)
            #print 'Cyclic: %s ' % (' -> '.join(c))
            continue
          stack.append(d)
          stackx[d] = self.type_dep.get(d, [])[:]
          #print 'Push: %s : %s' % (d, str(stackx[d]))
        else:
          #print 'Pop: %s' % (stack[-1])
          del stackx[stack[-1]]
          e = self.type[stack.pop()]['ethname']
          self.eth_type_ord1.append(e)
          x[e] = True
    i = 0
    while i < len(self.eth_dep_cycle):
      t = self.type[self.eth_dep_cycle[i][0]]['ethname']
      if self.dep_cycle_eth_type.has_key(t):
        self.dep_cycle_eth_type[t].append(i)
      else:
        self.dep_cycle_eth_type[t] = [i]
      i += 1

    #--- value dependencies and export -------------------
    self.eth_value_ord1 = []
    self.eth_vexport_ord = []
    for v in self.eth_value_ord:
      if self.eth_value[v]['export']:
        self.eth_vexport_ord.append(v)
      else:
        self.eth_value_ord1.append(v)

  #--- eth_vals ---------------------------------------------------------------
  def eth_vals(self, tname, vals):
    out = ""
    if (not self.eth_type[tname]['export'] & 0x02):
      out += "static "
    out += "const value_string %s_vals[] = {\n" % (tname)
    for (val, id) in vals:
      out += '  { %3s, "%s" },\n' % (val, id)
    out += "  { 0, NULL }\n};\n"
    return out

  #--- eth_bits ---------------------------------------------------------------
  def eth_bits(self, tname, bits):
    out = ""
    out += "static "
    out += "asn_namedbit %s_bits[] = {\n" % (tname)
    for (val, id) in bits:
      out += '  { %2d, &hf_%s_%s_%s, -1, -1, NULL, NULL },\n' % (val, self.proto, tname, id)
    out += "  { 0, NULL, 0, 0, NULL, NULL }\n};\n"
    return out

  #--- eth_type_fn_h ----------------------------------------------------------
  def eth_type_fn_h(self, tname):
    out = ""
    if (not self.eth_type[tname]['export'] & 0x01):
      out += "static "
    out += "int "
    if (self.OBer()):
      out += "dissect_%s_%s(gboolean implicit_tag, tvbuff_t *tvb, int offset, packet_info *pinfo, proto_tree *tree, int hf_index)" % (self.proto, tname)
    elif (self.NPer()):
      out += "dissect_%s_%s(tvbuff_t *tvb, int offset, packet_info *pinfo, proto_tree *tree, int hf_index, proto_item **item, void *private_data)" % (self.proto, tname)
    elif (self.OPer()):
      out += "dissect_%s_%s(tvbuff_t *tvb, int offset, packet_info *pinfo, proto_tree *tree, int hf_index)" % (self.proto, tname)
    out += ";\n"
    return out

  #--- eth_fn_call ------------------------------------------------------------
  def eth_fn_call(self, fname, ret=None, indent=2, par=None):
    out = indent * ' '
    if (ret):
      if (ret == 'return'):
        out += 'return '
      else:
        out += ret + ' = '
    out += fname + '('
    ind = len(out)
    for i in range(len(par)):
      if (i>0): out += ind * ' '
      out += ', '.join(par[i])
      if (i<(len(par)-1)): out += ',\n'
    out += ');\n'
    return out

  #--- eth_type_fn_hdr --------------------------------------------------------
  def eth_type_fn_hdr(self, tname):
    out = '\n'
    if (not self.eth_type[tname]['export'] & 0x01):
      out += "static "
    out += "int\n"
    if (self.OBer()):
      out += "dissect_%s_%s(gboolean implicit_tag _U_, tvbuff_t *tvb, int offset, packet_info *pinfo _U_, proto_tree *tree, int hf_index) {\n" % (self.proto, tname)
    elif (self.NPer()):
      out += "dissect_%s_%s(tvbuff_t *tvb, int offset, packet_info *pinfo _U_, proto_tree *tree, int hf_index, proto_item **item, void *private_data) {\n" % (self.proto, tname)
    elif (self.OPer()):
      out += "dissect_%s_%s(tvbuff_t *tvb, int offset, packet_info *pinfo _U_, proto_tree *tree, int hf_index) {\n" % (self.proto, tname)
    if self.conform.get_fn_presence(self.eth_type[tname]['ref'][0]):
      out += self.conform.get_fn_text(self.eth_type[tname]['ref'][0], 'FN_HDR')
    return out

  #--- eth_type_fn_ftr --------------------------------------------------------
  def eth_type_fn_ftr(self, tname):
    out = '\n'
    if self.conform.get_fn_presence(self.eth_type[tname]['ref'][0]):
      out += self.conform.get_fn_text(self.eth_type[tname]['ref'][0], 'FN_FTR')
    out += "  return offset;\n"
    out += "}\n"
    return out

  #--- eth_type_fn_body -------------------------------------------------------
  def eth_type_fn_body(self, tname, body, pars=None):
    if self.conform.get_fn_body_presence(self.eth_type[tname]['ref'][0]):
      out = self.conform.get_fn_text(self.eth_type[tname]['ref'][0], 'FN_BODY')
    elif pars:
      out = body % pars
    else:
      out = body
    return out

  #--- eth_output_fname -------------------------------------------------------
  def eth_output_fname (self, ftype, ext='c'):
    fn = ''
    if not ext in ('cnf',):
      fn += 'packet-' 
    fn += self.outnm
    if (ftype):
      fn += '-' + ftype
    fn += '.' + ext
    return fn

  #--- eth_output_hf ----------------------------------------------------------
  def eth_output_hf (self):
    if not len(self.eth_hf_ord) and not len(self.named_bit): return
    fn = self.eth_output_fname('hf')
    fx = file(fn, 'w')
    fx.write(eth_fhdr(fn))
    for f in self.eth_hf_ord:
      fx.write("%-50s/* %s */\n" % ("static int %s = -1;  " % (self.eth_hf[f]['fullname']), self.eth_hf[f]['ethtype']))
    if (self.named_bit):
      fx.write('/* named bits */\n')
    for nb in self.named_bit:
      fx.write("static int %s = -1;\n" % (nb['ethname']))
    fx.close()
    
  #--- eth_output_hf_arr ------------------------------------------------------
  def eth_output_hf_arr (self):
    if not len(self.eth_hf_ord) and not len(self.named_bit): return
    fn = self.eth_output_fname('hfarr')
    fx = file(fn, 'w')
    fx.write(eth_fhdr(fn))
    for f in self.eth_hf_ord:
      if len(self.eth_hf[f]['ref']) == 1:
        blurb = '"' + self.eth_hf[f]['ref'][0] + '"'
      else:
        blurb = '""'
      attr = self.eth_hf[f]['attr'].copy()
      attr['ABBREV'] = '"%s.%s"' % (self.proto, attr['ABBREV'])
      if not attr.has_key('BLURB'):
        attr['BLURB'] = blurb
      fx.write('    { &%s,\n' % (self.eth_hf[f]['fullname']))
      fx.write('      { %(NAME)s, %(ABBREV)s,\n' % attr)
      fx.write('        %(TYPE)s, %(DISPLAY)s, %(STRINGS)s, %(BITMASK)s,\n' % attr)
      fx.write('        %(BLURB)s, HFILL }},\n' % attr)
    for nb in self.named_bit:
      blurb = ''
      fx.write('    { &%s,\n' % (nb['ethname']))
      fx.write('      { "%s", "%s.%s",\n' % (nb['name'], self.proto, nb['name']))
      fx.write('        %s, %s, %s, %s,\n' % (nb['ftype'], nb['display'], nb['strings'], nb['bitmask']))
      fx.write('        "%s", HFILL }},\n' % (blurb))
    fx.close()

  #--- eth_output_ett ---------------------------------------------------------
  def eth_output_ett (self):
    fn = self.eth_output_fname('ett')
    fx = file(fn, 'w')
    fx.write(eth_fhdr(fn))
    fempty = True
    #fx.write("static gint ett_%s = -1;\n" % (self.proto))
    for t in self.eth_type_ord:
      if self.eth_type[t]['tree']:
        fx.write("static gint %s = -1;\n" % (self.eth_type[t]['tree']))
        fempty = False
    fx.close()
    if fempty: os.unlink(fn)

  #--- eth_output_ett_arr -----------------------------------------------------
  def eth_output_ett_arr(self):
    fn = self.eth_output_fname('ettarr')
    fx = file(fn, 'w')
    fx.write(eth_fhdr(fn))
    fempty = True
    #fx.write("    &ett_%s,\n" % (self.proto))
    for t in self.eth_type_ord:
      if self.eth_type[t]['tree']:
        fx.write("    &%s,\n" % (self.eth_type[t]['tree']))
        fempty = False
    fx.close()
    if fempty: os.unlink(fn)

  #--- eth_output_export ------------------------------------------------------
  def eth_output_export(self):
    if (not len(self.eth_export_ord)): return
    fn = self.eth_output_fname('exp', ext='h')
    fx = file(fn, 'w')
    fx.write(eth_fhdr(fn))
    for t in self.eth_export_ord:  # vals
      if (self.eth_type[t]['export'] & 0x02) and self.eth_type[t]['val'].eth_has_vals():
        fx.write("extern const value_string %s_vals[];\n" % (t))
    for t in self.eth_export_ord:  # functions
      if (self.eth_type[t]['export'] & 0x01):
        fx.write(self.eth_type_fn_h(t))
    fx.close()

  #--- eth_output_expcnf ------------------------------------------------------
  def eth_output_expcnf(self):
    if (not len(self.eth_export_ord)): return
    fn = self.eth_output_fname('exp', ext='cnf')
    fx = file(fn, 'w')
    fx.write(eth_fhdr(fn, comment = '#'))
    if self.Ber():
      fx.write('#.IMPORT_TAG\n')
      for t in self.eth_export_ord:  # tags
        if (self.eth_type[t]['export'] & 0x01):
          fx.write('%-24s ' % (t))
          fx.write('%s %s\n' % self.eth_type[t]['val'].GetTag(self))
      fx.write('#.END\n\n')
    fx.write('#.TYPE_ATTR\n')
    for t in self.eth_export_ord:  # attributes
      if (self.eth_type[t]['export'] & 0x01):
        fx.write('%-24s ' % (t))
        attr = self.eth_get_type_attr(self.eth_type[t]['ref'][0]).copy()
        fx.write('TYPE = %(TYPE)-9s  DISPLAY = %(DISPLAY)-9s  STRINGS = %(STRINGS)s  BITMASK = %(BITMASK)s\n' % attr)
    fx.write('#.END\n\n')
    fx.close()

  #--- eth_output_val ------------------------------------------------------
  def eth_output_val(self):
    if (not len(self.eth_value_ord1)): return
    fn = self.eth_output_fname('val', ext='h')
    fx = file(fn, 'w')
    fx.write(eth_fhdr(fn))
    for v in self.eth_value_ord1:
      fx.write("#define %-30s %s\n" % (v, self.eth_value[v]['value']))
    fx.close()

  #--- eth_output_valexp ------------------------------------------------------
  def eth_output_valexp(self):
    if (not len(self.eth_vexport_ord)): return
    fn = self.eth_output_fname('valexp', ext='h')
    fx = file(fn, 'w')
    fx.write(eth_fhdr(fn))
    for v in self.eth_vexport_ord:
      fx.write("#define %-30s %s\n" % (v, self.eth_value[v]['value']))
    fx.close()

  #--- eth_output_types -------------------------------------------------------
  def eth_output_types(self):
    def out_field(f):
      t = self.eth_hf[f]['ethtype']
      if (self.Ber()):
        x = {}
        for r in self.eth_hf[f]['ref']:
          x[self.field[r]['impl']] = self.field[r]['impl']
      else:
        x = {False : False}
      x = x.values()
      x.sort()
      for i in x:
        if (i):
          postfix = '_impl'
          impl = 'TRUE'
        else:
          postfix = ''
          impl = 'FALSE'
        if (self.Ber()):
          if (i): postfix = '_impl'; impl = 'TRUE'
          else:   postfix = '';      impl = 'FALSE'
          out = 'static int dissect_'+f+postfix+'(packet_info *pinfo, proto_tree *tree, tvbuff_t *tvb, int offset) {\n'
          par=((impl, 'tvb', 'offset', 'pinfo', 'tree', self.eth_hf[f]['fullname']),)
        else:
          out = 'static int dissect_'+f+'(tvbuff_t *tvb, int offset, packet_info *pinfo, proto_tree *tree) {\n'
          par=(('tvb', 'offset', 'pinfo', 'tree', self.eth_hf[f]['fullname']),)
        out += self.eth_fn_call('dissect_%s_%s' % (self.eth_type[t]['proto'], t), ret='return',
                                par=par)
        out += '}\n'
      return out
    #end out_field()
    fn = self.eth_output_fname('fn')
    fx = file(fn, 'w')
    fx.write(eth_fhdr(fn))
    pos = fx.tell()
    if self.eth_dep_cycle:
      fx.write('/*--- Cyclic dependencies ---*/\n\n')
      i = 0
      while i < len(self.eth_dep_cycle):
        t = self.type[self.eth_dep_cycle[i][0]]['ethname']
        if self.dep_cycle_eth_type[t][0] != i: i += 1; continue
        fx.write(''.join(map(lambda i: '/* %s */\n' % ' -> '.join(self.eth_dep_cycle[i]), self.dep_cycle_eth_type[t])))
        fx.write(self.eth_type_fn_h(t))
        if (not self.new):
          fx.write('\n')
          for f in self.eth_hf_ord:
            if (self.eth_hf[f]['ethtype'] == t):
              fx.write(out_field(f))
        fx.write('\n')
        i += 1
      fx.write('\n')
    if (not self.new):  # fields for imported types
      fx.write('/*--- Fields for imported types ---*/\n\n')
      for f in self.eth_hf_ord:
        if (self.eth_type[self.eth_hf[f]['ethtype']]['import']):
          fx.write(out_field(f))
      fx.write('\n')
    for t in self.eth_type_ord1:
      if self.eth_type[t]['import']:
        continue
      if self.eth_type[t]['val'].eth_has_vals():
        if self.eth_type[t]['no_emit'] & 0x02:
          pass
        elif self.eth_type[t]['user_def'] & 0x02:
          fx.write("extern const value_string %s_vals[];\n" % (t))
        else:
          fx.write(self.eth_type[t]['val'].eth_type_vals(self.proto, t, self))
      if self.eth_type[t]['no_emit'] & 0x01:
        pass
      elif self.eth_type[t]['user_def'] & 0x01:
        fx.write(self.eth_type_fn_h(t))
      else:
        fx.write(self.eth_type[t]['val'].eth_type_fn(self.proto, t, self))
      if (not self.new and not self.dep_cycle_eth_type.has_key(t)):
        for f in self.eth_hf_ord:
          if (self.eth_hf[f]['ethtype'] == t):
            fx.write(out_field(f))
      fx.write('\n')
    fempty = pos == fx.tell()
    fx.close()
    if fempty: os.unlink(fn)

  def dupl_report(self):
    # types
    tmplist = self.eth_type_dupl.keys()
    tmplist.sort()
    for t in tmplist:
      msg = "The same type names for different types. Explicit type renaming is recommended.\n"
      msg += t + "\n"
      x = ''
      for tt in self.eth_type_dupl[t]:
        msg += " %-20s %s\n" % (t+str(x), tt)
        if not x: x = 1
        else: x += 1
      warnings.warn_explicit(msg, UserWarning, '', '')
    # fields
    tmplist = self.eth_hf_dupl.keys()
    tmplist.sort()
    for f in tmplist:
      msg = "The same field names for different types. Explicit field renaming is recommended.\n"
      msg += f + "\n"
      for tt in self.eth_hf_dupl[f].keys():
        msg += " %-20s %-20s " % (self.eth_hf_dupl[f][tt], tt)
        msg += ", ".join(self.eth_hf[self.eth_hf_dupl[f][tt]]['ref'])
        msg += "\n"
      warnings.warn_explicit(msg, UserWarning, '', '')

#--- EthCnf -------------------------------------------------------------------
import re
class EthCnf:
  def __init__(self):
    self.tblcfg = {}
    self.table = {}
    self.fn = {}
    #                                   Value name             Default value       Duplicity check   Usage check
    self.tblcfg['EXPORTS']         = { 'val_nm' : 'flag',     'val_dflt' : 0,     'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['PDU']             = { 'val_nm' : 'attr',     'val_dflt' : None,  'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['USER_DEFINED']    = { 'val_nm' : 'flag',     'val_dflt' : 0,     'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['NO_EMIT']         = { 'val_nm' : 'flag',     'val_dflt' : 0,     'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['MODULE_IMPORT']   = { 'val_nm' : 'proto',    'val_dflt' : None,  'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['OMIT_ASSIGNMENT'] = { 'val_nm' : 'omit',     'val_dflt' : False, 'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['TYPE_RENAME']     = { 'val_nm' : 'eth_name', 'val_dflt' : None,  'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['FIELD_RENAME']    = { 'val_nm' : 'eth_name', 'val_dflt' : None,  'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['IMPORT_TAG']      = { 'val_nm' : 'ttag',     'val_dflt' : (),    'chk_dup' : True, 'chk_use' : False }
    self.tblcfg['FN_PARS']         = { 'val_nm' : 'pars',     'val_dflt' : {},    'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['TYPE_ATTR']       = { 'val_nm' : 'attr',     'val_dflt' : {},    'chk_dup' : True, 'chk_use' : False }
    self.tblcfg['ETYPE_ATTR']      = { 'val_nm' : 'attr',     'val_dflt' : {},    'chk_dup' : True, 'chk_use' : False }
    self.tblcfg['FIELD_ATTR']      = { 'val_nm' : 'attr',     'val_dflt' : {},    'chk_dup' : True, 'chk_use' : True }
    self.tblcfg['EFIELD_ATTR']     = { 'val_nm' : 'attr',     'val_dflt' : {},    'chk_dup' : True, 'chk_use' : True }


    for k in self.tblcfg.keys() :
      self.table[k] = {}

  def add_item(self, table, key, fn, lineno, **kw):
    if self.tblcfg[table]['chk_dup'] and self.table[table].has_key(key):
      warnings.warn_explicit("Duplicated %s for %s. Previous one is at %s:%d" % 
                             (table, key, self.table[table][key]['fn'], self.table[table][key]['lineno']), 
                             UserWarning, fn, lineno)
      return
    self.table[table][key] = {'fn' : fn, 'lineno' : lineno, 'used' : False}
    self.table[table][key].update(kw)

  def check_item(self, table, key):
    return self.table[table].has_key(key)

  def check_item_value(self, table, key, **kw):
    return self.table[table].has_key(key) and self.table[table][key].has_key(kw.get('val_nm', self.tblcfg[table]['val_nm']))

  def use_item(self, table, key, **kw):
    vdflt = kw.get('val_dflt', self.tblcfg[table]['val_dflt'])
    if not self.table[table].has_key(key): return vdflt
    vname = kw.get('val_nm', self.tblcfg[table]['val_nm'])
    self.table[table][key]['used'] = True
    return self.table[table][key].get(vname, vdflt)

  def add_fn_line(self, name, ctx, line, fn, lineno):
    if not self.fn.has_key(name):
      self.fn[name] = {'FN_HDR' : None, 'FN_FTR' : None, 'FN_BODY' : None}
    if (self.fn[name][ctx]):
      self.fn[name][ctx]['text'] += line
    else:
      self.fn[name][ctx] = {'text' : line, 'used' : False,
                             'fn' : fn, 'lineno' : lineno}
  def get_fn_presence(self, name):
    #print "get_fn_presence('%s'):%s" % (name, str(self.fn.has_key(name)))
    #if self.fn.has_key(name): print self.fn[name]
    return self.fn.has_key(name)
  def get_fn_body_presence(self, name):
    return self.fn.has_key(name) and self.fn[name]['FN_BODY']
  def get_fn_text(self, name, ctx):
    if (not self.fn.has_key(name)):
      return '';
    if (not self.fn[name][ctx]):
      return '';
    return self.fn[name][ctx]['text']

  def read(self, fn):
    def get_par(line, pmin, pmax, fn, lineno):
      par = line.split(None, pmax)
      for i in range(len(par)):
        if par[i] == '-':
          par[i] = None
        if par[i][0] == '#':
          par[i:] = []
          break
      if len(par) < pmin:
        warnings.warn_explicit("Too few parameters. At least %d parameters are required" % (pmin), UserWarning, fn, lineno)
        return None
      if len(par) > pmax:
        warnings.warn_explicit("Too many parameters. Only %d parameters are allowed" % (pmax), UserWarning, fn, lineno)
        return par[0:pmax]
      return par

    def get_par_nm(line, pnum, fn, lineno):
      if pnum:
        par = line.split(None, 1)
      else:
        par = [line,]
      for i in range(len(par)):
        if par[i][0] == '#':
          par[i:] = []
          break
      if len(par) < pnum:
        warnings.warn_explicit("Too few parameters.", UserWarning, fn, lineno)
        return None
      if len(par) > pnum:
        nmpar = par[pnum]
      else:
        nmpar = ''
      nmpars = {}
      nmpar_first = re.compile(r'^\s*(?P<attr>[_A-Z][_A-Z0-9]*)\s*=\s*')
      nmpar_next = re.compile(r'\s+(?P<attr>[_A-Z][_A-Z0-9]*)\s*=\s*')
      nmpar_end = re.compile(r'\s*$')
      result = nmpar_first.search(nmpar)
      pos = 0
      while result:
        k = result.group('attr')
        pos = result.end()
        result = nmpar_next.search(nmpar, pos)
        p1 = pos
        if result:
          p2 = result.start()
        else:
          p2 = nmpar_end.search(nmpar, pos).start()
        v = nmpar[p1:p2]
        nmpars[k] = v
      par[pnum] = nmpars
      return par

    f = open(fn, "r")
    directive = re.compile(r'^\s*#\.(?P<name>[A-Z_]+)\s+')
    comment = re.compile(r'^\s*#[^.]')
    empty = re.compile(r'^\s*$')
    lineno = 0
    ctx = None
    name = ''
    stack = []
    while 1:
      line = f.readline()
      lineno += 1
      if not line:
        f.close()
        if stack:
          frec = stack.pop()
          fn, f, lineno = frec['fn'], frec['f'], frec['lineno']
          continue
        else: 
          break
      if comment.search(line): continue
      result = directive.search(line)
      if result:  # directive
        if result.group('name') in ('EXPORTS', 'USER_DEFINED', 'NO_EMIT', 'MODULE_IMPORT', 'OMIT_ASSIGNMENT', 'TYPE_RENAME', 'FIELD_RENAME', 'IMPORT_TAG',
                                    'TYPE_ATTR', 'ETYPE_ATTR', 'FIELD_ATTR', 'EFIELD_ATTR'):
          ctx = result.group('name')
        elif result.group('name') in ('FN_HDR', 'FN_FTR', 'FN_BODY'):
          par = get_par(line[result.end():], 1, 1, fn=fn, lineno=lineno)
          if not par: continue
          ctx = result.group('name')
          name = par[0]
        elif result.group('name') == 'FN_PARS':
          par = get_par(line[result.end():], 0, 1, fn=fn, lineno=lineno)
          ctx = result.group('name')
          if not par:
            name = None
          else:
            name = par[0]
        elif result.group('name') == 'INCLUDE':
          par = get_par(line[result.end():], 1, 1, fn=fn, lineno=lineno)
          if not par: continue
          fnew = open(par[0], "r")
          stack.append({'fn' : fn, 'f' : f, 'lineno' : lineno})
          fn, f, lineno = par[0], fnew, 0
        elif result.group('name') == 'END':
          ctx = None
        else:
          warnings.warn_explicit("Unknown directive '%s'" % (result.group('name')), UserWarning, fn, lineno)
        continue
      if not ctx:
        if not empty.match(line):
          warnings.warn_explicit("Non-empty line in empty context", UserWarning, fn, lineno)
      elif ctx in ('EXPORTS', 'USER_DEFINED', 'NO_EMIT'):
        if empty.match(line): continue
        par = get_par(line, 1, 2, fn=fn, lineno=lineno)
        if not par: continue
        flag = 0x03
        if (len(par)>=2):
          if (par[1] == 'WITH_VALS'):
            flag = 0x03
          elif (par[1] == 'WITHOUT_VALS'):
            flag = 0x01
          elif (par[1] == 'ONLY_VALS'):
            flag = 0x02
          else:
            warnings.warn_explicit("Unknown parameter value '%s'" % (par[1]), UserWarning, fn, lineno)
        self.add_item(ctx, par[0], flag=flag, fn=fn, lineno=lineno)
      elif ctx == 'MODULE_IMPORT':
        if empty.match(line): continue
        par = get_par(line, 2, 2, fn=fn, lineno=lineno)
        if not par: continue
        self.add_item('MODULE_IMPORT', par[0], proto=par[1], fn=fn, lineno=lineno)
      elif ctx == 'IMPORT_TAG':
        if empty.match(line): continue
        par = get_par(line, 3, 3, fn=fn, lineno=lineno)
        if not par: continue
        self.add_item('IMPORT_TAG', par[0], ttag=(par[1], par[2]), fn=fn, lineno=lineno)
      elif ctx == 'OMIT_ASSIGNMENT':
        if empty.match(line): continue
        par = get_par(line, 1, 1, fn=fn, lineno=lineno)
        if not par: continue
        self.add_item('OMIT_ASSIGNMENT', par[0], omit=True, fn=fn, lineno=lineno)
      elif ctx == 'TYPE_RENAME':
        if empty.match(line): continue
        par = get_par(line, 2, 2, fn=fn, lineno=lineno)
        if not par: continue
        self.add_item('TYPE_RENAME', par[0], eth_name=par[1], fn=fn, lineno=lineno)
      elif ctx == 'FIELD_RENAME':
        if empty.match(line): continue
        par = get_par(line, 2, 2, fn=fn, lineno=lineno)
        if not par: continue
        self.add_item('FIELD_RENAME', par[0], eth_name=par[1], fn=fn, lineno=lineno)
      elif ctx in ('TYPE_ATTR', 'ETYPE_ATTR', 'FIELD_ATTR', 'EFIELD_ATTR'):
        if empty.match(line): continue
        par = get_par_nm(line, 1, fn=fn, lineno=lineno)
        if not par: continue
        self.add_item(ctx, par[0], attr=par[1], fn=fn, lineno=lineno)
      elif ctx in ('FN_HDR', 'FN_FTR', 'FN_BODY'):
        self.add_fn_line(name, ctx, line, fn=fn, lineno=lineno)

  def unused_report(self):
    tbls = self.table.keys()
    tbls.sort()
    for t in tbls:
      if not self.tblcfg[t]['chk_use']: continue
      keys = self.table[t].keys()
      keys.sort()
      for k in keys:
        if not self.table[t][k]['used']:
          warnings.warn_explicit("Unused %s for %s" % (t, k),
                                  UserWarning, self.table[t][k]['fn'], self.table[t][k]['lineno'])


#--- Node ---------------------------------------------------------------------
class Node:
    def __init__(self,*args, **kw):
        if len (args) == 0:
            self.type = self.__class__.__name__
        else:
            assert (len(args) == 1)
            self.type = args[0]
        self.__dict__.update (kw)
    def str_child (self, key, child, depth):
        indent = " " * (2 * depth)
        keystr = indent + key + ": "
        if key == 'type': # already processed in str_depth
            return ""
        if isinstance (child, Node): # ugh
            return keystr + "\n" + child.str_depth (depth+1)
        if type (child) == type ([]):
            l = []
            for x in child:
              if isinstance (x, Node):
                l.append (x.str_depth (depth+1))
              else:
                l.append (indent + "  " + str(x) + "\n")
            return keystr + "[\n" + ''.join (l) + indent + "]\n"
        else:
            return keystr + str (child) + "\n"
    def str_depth (self, depth): # ugh
        indent = " " * (2 * depth)
        l = ["%s%s" % (indent, self.type)]
        l.append ("".join (map (lambda (k,v): self.str_child (k, v, depth + 1),
                                self.__dict__.items ())))
        return "\n".join (l)
    def __str__(self):
        return "\n" + self.str_depth (0)
    def to_python (self, ctx):
        return self.str_depth (ctx.indent_lev)

    def eth_reg(self, ident, ectx):
        pass

#--- value_assign -------------------------------------------------------------
class value_assign (Node):
  def __init__(self,*args, **kw) :
    Node.__init__ (self,*args, **kw)

  def eth_reg(self, ident, ectx):
    ectx.eth_reg_vassign(self)
    ectx.eth_reg_value(self.ident, self.typ, self.val)


#--- Type ---------------------------------------------------------------------
class Type (Node):
  def __init__(self,*args, **kw) :
    self.name = None
    self.constr = None
    Node.__init__ (self,*args, **kw)

  def IsNamed(self):
    if self.name is None :
      return False
    else:
      return True

  def HasConstraint(self):
    if self.constr is None :
      return False
    else :
      return True

  def HasOwnTag(self):
    return self.__dict__.has_key('tag')

  def HasImplicitTag(self):
    return self.HasOwnTag() and (self.tag.mode == 'IMPLICIT')

  def IndetermTag(self, ectx):
    return False

  def SetTag(self, tag):
    self.tag = tag

  def GetTag(self, ectx):
    if (self.HasOwnTag()):
      return self.tag.GetTag(ectx)
    else:
      return self.GetTTag(ectx)

  def GetTTag(self, ectx):
    print "#Unhandled  GetTTag() in %s" % (self.type)
    print self.str_depth(1)
    return ('BER_CLASS_unknown', 'TAG_unknown')

  def SetName(self, name) :
    self.name = name

  def AddConstraint(self, constr):
    if not self.HasConstraint():
      self.constr = constr
    else:
      self.constr = Constraint(type = 'Intersection', subtype = [self.constr, constr])

  def eth_tname(self):
    return '#' + self.type + '_' + str(id(self))

  def eth_ftype(self):
    return ('FT_NONE', 'BASE_NONE')

  def eth_strings(self):
    return 'NULL'

  def eth_need_tree(self):
    return False

  def eth_has_vals(self):
    return False

  def eth_named_bits(self):
    return None

  def eth_reg_sub(self, ident, ectx):
    pass

  def eth_reg(self, ident, ectx, idx='', parent=None):
    nm = ''
    if ident and self.IsNamed ():
      nm = ident + '/' + self.name
    elif self.IsNamed():
      nm = self.name
    elif ident:
      nm = ident
    if not ident and ectx.conform.use_item('OMIT_ASSIGNMENT', nm): return # Assignment to omit
    if not ident:  # Assignment
      ectx.eth_reg_assign(nm, self)
      if self.type == 'Type_Ref':
        ectx.eth_reg_type(nm, self)
    if self.type == 'Type_Ref':
      if ectx.conform.check_item('TYPE_RENAME', nm) or ectx.conform.get_fn_presence(nm):
        ectx.eth_reg_type(nm, self)  # new type
        trnm = nm
      else:
        trnm = self.val
    else:
      ectx.eth_reg_type(nm, self)
    if ident:
      if self.type == 'Type_Ref':
        ectx.eth_reg_field(nm, trnm, idx=idx, parent=parent, impl=self.HasImplicitTag())
      else:
        ectx.eth_reg_field(nm, nm, idx=idx, parent=parent, impl=self.HasImplicitTag())
    self.eth_reg_sub(nm, ectx)

  def eth_get_size_constr(self, ):
    minv = '-1'
    maxv = '-1'
    ext = 'FALSE'
    if not self.HasConstraint():
      minv = '-1'
      maxv = '-1'
      ext = 'FALSE'
    elif self.constr.type == 'Size' and (self.constr.subtype.type == 'SingleValue' or self.constr.subtype.type == 'ValueRange'):
      if self.constr.subtype.type == 'SingleValue':
        minv = self.constr.subtype.subtype
        maxv = self.constr.subtype.subtype
      else:
        minv = self.constr.subtype.subtype[0]
        maxv = self.constr.subtype.subtype[1]
      if hasattr(self.constr.subtype, 'ext') and self.constr.subtype.ext:
        ext = 'TRUE'
      else:
        ext = 'FALSE'
    return (minv, maxv, ext)

  def eth_type_vals(self, proto, tname, ectx):
    if self.eth_has_vals():
      print "#Unhandled  eth_type_vals('%s', '%s') in %s" % (proto, tname, self.type)
      print self.str_depth(1)
    return ''

  def eth_type_fn(self, proto, tname, ectx):
    print "#Unhandled  eth_type_fn('%s', '%s') in %s" % (proto, tname, self.type)
    print self.str_depth(1)
    return ''

#--- Value --------------------------------------------------------------------
class Value (Node):
  def __init__(self,*args, **kw) :
    self.name = None
    Node.__init__ (self,*args, **kw)

  def SetName(self, name) :
    self.name = name

  def to_str(self):
    return str(self)

  def get_dep(self):
    return None

#--- Constraint ---------------------------------------------------------------
class Constraint (Node):
  def to_python (self, ctx):
    print "Ignoring constraint:", self.type
    return self.subtype.typ.to_python (ctx)
  def __str__ (self):
    return "Constraint: type=%s, subtype=%s" % (self.type, self.subtype)

  def eth_constrname(self):
    ext = ''
    if hasattr(self, 'ext') and self.ext:
      ext = '_'
    if self.type == 'SingleValue':
      return str(self.subtype) + ext
    elif self.type == 'ValueRange':
      return str(self.subtype[0]) + '_' + str(self.subtype[1]) + ext
    elif self.type == 'Size':
      return 'SIZE_' + self.subtype.eth_constrname() + ext
    else:
      return 'CONSTR' + str(id(self)) + ext


class Module (Node):
    def to_python (self, ctx):
        ctx.tag_def = self.tag_def.dfl_tag
        return """#%s
%s""" % (self.ident, self.body.to_python (ctx))

    def to_eth (self, ectx):
        self.body.to_eth(ectx)

class Module_Body (Node):
    def to_python (self, ctx):
        # XXX handle exports, imports.
        l = map (lambda x: x.to_python (ctx), self.assign_list)
        l = [a for a in l if a <> '']
        return "\n".join (l)

    def to_eth(self, ectx):
        for i in self.imports:
          mod = i.module.val
          proto = ectx.conform.use_item('MODULE_IMPORT', mod, val_dflt=mod.replace('-', '_'))
          for s in i.symbol_list:
            if isinstance(s, Type_Ref):
              ectx.eth_import_type(s.val, mod, proto)
            else:
              ectx.eth_import_value(s, mod, proto)
        for a in self.assign_list:
          a.eth_reg('', ectx)

class Default_Tags (Node):
    def to_python (self, ctx): # not to be used directly
        assert (0)

# XXX should just calculate dependencies as we go along.
def calc_dependencies (node, dict, trace = 0):
    if not hasattr (node, '__dict__'):
        if trace: print "#returning, node=", node
        return
    if isinstance (node, Type_Ref):
        dict [node.val] = 1
        if trace: print "#Setting", node.val
        return
    for (a, val) in node.__dict__.items ():
        if trace: print "# Testing node ", node, "attr", a, " val", val
        if a[0] == '_':
            continue
        elif isinstance (val, Node):
            calc_dependencies (val, dict, trace)
        elif isinstance (val, type ([])):
            for v in val:
                calc_dependencies (v, dict, trace)
    
                          
class Type_Assign (Node):
    def __init__ (self, *args, **kw):
        Node.__init__ (self, *args, **kw)
        if isinstance (self.val, Tag): # XXX replace with generalized get_typ_ignoring_tag (no-op for Node, override in Tag)
            to_test = self.val.typ
        else:
            to_test = self.val
        if isinstance (to_test, SequenceType):
            to_test.sequence_name = self.name.name
            
    def to_python (self, ctx):
        dep_dict = {}
        calc_dependencies (self.val, dep_dict, 0)
        depend_list = dep_dict.keys ()
        return ctx.register_assignment (self.name.name,
                                        self.val.to_python (ctx),
                                        depend_list)

class PyQuote (Node):
    def to_python (self, ctx):
        return ctx.register_pyquote (self.val)

#--- Type_Ref -----------------------------------------------------------------
class Type_Ref (Type):
  def to_python (self, ctx):
    return self.val

  def eth_reg_sub(self, ident, ectx):
    ectx.eth_dep_add(ident, self.val)

  def eth_tname(self):
    return self.val

  def GetTTag(self, ectx):
    if (ectx.type[self.val]['import']):
      if not ectx.type[self.val].has_key('ttag'):
        if not ectx.conform.check_item('IMPORT_TAG', self.val):
          msg = 'Missing tag information for imported type %s from %s (%s)' % (self.val, ectx.type[self.val]['import'], ectx.type[self.val]['proto'])
          warnings.warn_explicit(msg, UserWarning, '', '')
        ectx.type[self.val]['ttag'] = ectx.conform.use_item('IMPORT_TAG', self.val, val_dflt=('-1 /*imported*/', '-1 /*imported*/'))
      return ectx.type[self.val]['ttag']
    else:
      return ectx.type[self.val]['val'].GetTag(ectx)

  def IndetermTag(self, ectx):
    if (ectx.type[self.val]['import']):
      return False
    else:
      return ectx.type[self.val]['val'].IndetermTag(ectx)

  def eth_type_fn(self, proto, tname, ectx):
    out = ectx.eth_type_fn_hdr(tname)
    t = ectx.type[self.val]['ethname']
    if (ectx.OBer()):
      body = ectx.eth_fn_call('dissect_%s_%s' % (ectx.eth_type[t]['proto'], t), ret='offset',
                              par=(('implicit_tag', 'tvb', 'offset', 'pinfo', 'tree', 'hf_index'),))
    elif (ectx.NPer()):
      body = ectx.eth_fn_call('dissect_%s_%s' % (ectx.eth_type[t]['proto'], t), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree'),
                                   ('hf_index', 'item', 'private_data')))
    elif (ectx.OPer()):
      body = ectx.eth_fn_call('dissect_%s_%s' % (ectx.eth_type[t]['proto'], t), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),))
    else:
      body = '#error Can not decode %s' % (tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

#--- SqType -----------------------------------------------------------
class SqType (Type):
  def out_item(self, f, val, optional, ext, ectx):
    ef = ectx.field[f]['ethname']
    efd = ef
    if (ectx.OBer() and ectx.field[f]['impl']):
      efd += '_impl'
    if (ectx.encoding == 'ber'):
      #print "optional=%s, e.val.HasOwnTag()=%s, e.val.IndetermTag()=%s" % (str(e.optional), str(e.val.HasOwnTag()), str(e.val.IndetermTag(ectx)))
      #print val.str_depth(1)
      opt = ''
      if (optional):
        opt = 'BER_FLAGS_OPTIONAL'
      if (not val.HasOwnTag()):
        if (opt): opt += '|'
        opt += 'BER_FLAGS_NOOWNTAG'
      elif (val.HasImplicitTag()):
        if (opt): opt += '|'
        opt += 'BER_FLAGS_IMPLTAG'
      if (val.IndetermTag(ectx)):
        if (opt): opt += '|'
        opt += 'BER_FLAGS_NOTCHKTAG'
      if (not opt): opt = '0'
    else:
      if optional:
        opt = 'ASN1_OPTIONAL'
      else:
        opt = 'ASN1_NOT_OPTIONAL'
    if (ectx.OBer()):
      (tc, tn) = val.GetTag(ectx)
      out = '  { %-13s, %s, %s, dissect_%s },\n' \
            % (tc, tn, opt, efd)
    elif (ectx.NPer()):
      out = '  { &%-30s, %-23s, %-17s, dissect_%s_%s },\n' \
            % (ef, ext, opt, ectx.eth_type[ectx.eth_hf[ef]['ethtype']]['proto'], ectx.eth_hf[ef]['ethtype'])
    elif (ectx.OPer()):
      out = '  { %-30s, %-23s, %-17s, dissect_%s },\n' \
            % ('"'+val.name+'"', ext, opt, efd)
    else:
      out = ''
    return out   

#--- SequenceOfType -----------------------------------------------------------
class SequenceOfType (SqType):
  def to_python (self, ctx):
    # name, tag (None for no tag, EXPLICIT() for explicit), typ)
    # or '' + (1,) for optional
    sizestr = ''
    if self.size_constr <> None:
        print "#Ignoring size constraint:", self.size_constr.subtype
    return "%sasn1.SEQUENCE_OF (%s%s)" % (ctx.spaces (),
                                          self.val.to_python (ctx),
                                          sizestr)

  def eth_reg_sub(self, ident, ectx):
    itmnm = ident
    if not self.val.IsNamed ():
      itmnm += '/' + '_item'
    self.val.eth_reg(itmnm, ectx, idx='[##]', parent=ident)

  def eth_tname(self):
    return "SEQUNCE_OF_" + self.val.eth_tname()

  def eth_ftype(self):
    return ('FT_UINT32', 'BASE_DEC')

  def eth_need_tree(self):
    return True

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_SEQUENCE')

  def eth_type_fn(self, proto, tname, ectx):
    fname = ectx.eth_type[tname]['ref'][0]
    if self.val.IsNamed ():
      f = fname + '/' + self.val.name
    else:
      f = fname + '/' + '_item'
    ef = ectx.field[f]['ethname']
    out = ''
    if (ectx.Ber()):
      out = "static ber_sequence %s_sequence_of[1] = {\n" % (tname)
      out += self.out_item(f, self.val, False, '', ectx)
      out += "};\n"
    out += ectx.eth_type_fn_hdr(tname)
    if (ectx.OBer()):
      body = ectx.eth_fn_call('dissect_ber_sequence_of' + ectx.pvp(), ret='offset',
                                par=(('implicit_tag', 'pinfo', 'tree', 'tvb', 'offset'),
                                     (tname+'_sequence_of', 'hf_index', ectx.eth_type[tname]['tree'])))
    elif (ectx.NPer()):
      body = ectx.eth_fn_call('dissect_per_sequence_of' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree'),
                                   ('hf_index', 'item', 'private_data'),
                                   (ectx.eth_type[tname]['tree'], ef, 'dissect_%s_%s' % (ectx.eth_type[ectx.eth_hf[ef]['ethtype']]['proto'], ectx.eth_hf[ef]['ethtype']))))
    elif (ectx.OPer()):
      body = ectx.eth_fn_call('dissect_per_sequence_of' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                   (ectx.eth_type[tname]['tree'], 'dissect_'+ef)))
    else:
      body = '#error Can not decode %s' % (tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out


#--- SetOfType ----------------------------------------------------------------
class SetOfType (SqType):
  def eth_reg_sub(self, ident, ectx):
    itmnm = ident
    if not self.val.IsNamed ():
      itmnm += '/' + '_item'
    self.val.eth_reg(itmnm, ectx, idx='(##)', parent=ident)

  def eth_tname(self):
      return "SET_OF_" + self.val.eth_tname()

  def eth_ftype(self):
    return ('FT_UINT32', 'BASE_DEC')

  def eth_need_tree(self):
    return True

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_SET')

  def eth_type_fn(self, proto, tname, ectx):
    fname = ectx.eth_type[tname]['ref'][0]
    f = fname + '/' + '_item'
    ef = ectx.field[f]['ethname']
    out = ''
    if (ectx.Ber()):
      out = "static ber_sequence %s_set_of[1] = {\n" % (tname)
      out += self.out_item(f, self.val, False, '', ectx)
      out += "};\n"
    out += ectx.eth_type_fn_hdr(tname)
    if (ectx.OBer()):
      body = ectx.eth_fn_call('dissect_ber_set_of' + ectx.pvp(), ret='offset',
                                par=(('implicit_tag', 'pinfo', 'tree', 'tvb', 'offset'),
                                     (tname+'_set_of', 'hf_index', ectx.eth_type[tname]['tree'])))
    elif (ectx.NPer()):
      body = ectx.eth_fn_call('dissect_per_set_of' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree'),
                                   ('hf_index', 'item', 'private_data'),
                                   (ectx.eth_type[tname]['tree'], ef, 'dissect_%s_%s' % (ectx.eth_type[ectx.eth_hf[ef]['ethtype']]['proto'], ectx.eth_hf[ef]['ethtype']))))
    else:
      body = '#error Can not decode %s' % (tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

def mk_tag_str (ctx, cls, typ, num):

    # XXX should do conversion to int earlier!
    val = int (num)
    typ = typ.upper()
    if typ == 'DEFAULT':
        typ = ctx.tags_def
    return 'asn1.%s(%d,cls=asn1.%s_FLAG)' % (typ, val, cls) # XXX still ned

class Tag (Node):
  def to_python (self, ctx):
    return 'asn1.TYPE(%s,%s)' % (mk_tag_str (ctx, self.tag.cls,
                                                self.tag_typ,
                                                self.tag.num),
                                    self.typ.to_python (ctx))
  def GetTag(self, ectx):
    tc = ''
    if (self.cls == 'UNIVERSAL'): tc = 'BER_CLASS_UNI'
    elif (self.cls == 'APPLICATION'): tc = 'BER_CLASS_APP'
    elif (self.cls == 'CONTEXT'): tc = 'BER_CLASS_CON'
    elif (self.cls == 'PRIVATE'): tc = 'BER_CLASS_PRI'
    return (tc, self.num)
 
#--- SequenceType -------------------------------------------------------------
class SequenceType (SqType):
    def to_python (self, ctx):
        # name, tag (None for no tag, EXPLICIT() for explicit), typ)
        # or '' + (1,) for optional
        # XXX should also collect names for SEQUENCE inside SEQUENCE or
        # CHOICE or SEQUENCE_OF (where should the SEQUENCE_OF name come
        # from?  for others, element or arm name would be fine)
        seq_name = getattr (self, 'sequence_name', None)
        if seq_name == None:
            seq_name = 'None'
        else:
            seq_name = "'" + seq_name + "'"
        if self.__dict__.has_key('ext_list'):
          return "%sasn1.SEQUENCE ([%s], ext=[%s], seq_name = %s)" % (ctx.spaces (), 
                                   self.elts_to_py (self.elt_list, ctx),
                                   self.elts_to_py (self.ext_list, ctx), seq_name)
        else:
          return "%sasn1.SEQUENCE ([%s]), seq_name = %s" % (ctx.spaces (), 
                                   self.elts_to_py (self.elt_list, ctx), seq_name)
    def elts_to_py (self, list, ctx):
        # we have elt_type, val= named_type, maybe default=, optional=
        # named_type node: either ident = or typ =
        # need to dismember these in order to generate Python output syntax.
        ctx.indent ()
        def elt_to_py (e):
            assert (e.type == 'elt_type')
            nt = e.val
            optflag = e.optional
#            assert (not hasattr (e, 'default')) # XXX add support for DEFAULT!
            assert (nt.type == 'named_type')
            tagstr = 'None'
            identstr = nt.ident
            if hasattr (nt.typ, 'type') and nt.typ.type == 'tag': # ugh
                tagstr = mk_tag_str (ctx,nt.typ.tag.cls,
                                     nt.typ.tag.tag_typ,nt.typ.tag.num)
        

                nt = nt.typ
            return "('%s',%s,%s,%d)" % (identstr, tagstr,
                                      nt.typ.to_python (ctx), optflag)
        indentstr = ",\n" + ctx.spaces ()
        rv = indentstr.join ([elt_to_py (e) for e in list])
        ctx.outdent ()
        return rv

    def eth_reg_sub(self, ident, ectx):
        for e in (self.elt_list):
            e.val.eth_reg(ident, ectx, parent=ident)
        if hasattr(self, 'ext_list'):
            for e in (self.ext_list):
                e.val.eth_reg(ident, ectx, parent=ident)

    def eth_need_tree(self):
      return True

    def GetTTag(self, ectx):
      return ('BER_CLASS_UNI', 'BER_UNI_TAG_SEQUENCE')

    def eth_type_fn(self, proto, tname, ectx):
      fname = ectx.eth_type[tname]['ref'][0]
      if (ectx.encoding == 'ber'):
        out = "static ber_sequence %s_sequence[] = {\n" % (tname)
      else:
        out = "static per_sequence%s_t %s_sequence%s[] = {\n" % (ectx.pvp(), tname, ectx.pvp())
      if hasattr(self, 'ext_list'):
        ext = 'ASN1_EXTENSION_ROOT'
      else:
        ext = 'ASN1_NO_EXTENSIONS'
      for e in (self.elt_list):
        f = fname + '/' + e.val.name
        out += self.out_item(f, e.val, e.optional, ext, ectx)
      if hasattr(self, 'ext_list'):
        for e in (self.ext_list):
          f = fname + '/' + e.val.name
          out += self.out_item(f, e.val, e.optional, 'ASN1_NOT_EXTENSION_ROOT', ectx)
      if (ectx.encoding == 'ber'):
        out += "  { 0, 0, 0, NULL }\n};\n"
      else:
        out += "  { NULL, 0, 0, NULL }\n};\n"
      out += ectx.eth_type_fn_hdr(tname)
      if (ectx.OBer()):
        body = ectx.eth_fn_call('dissect_ber_sequence' + ectx.pvp(), ret='offset',
                                par=(('implicit_tag', 'pinfo', 'tree', 'tvb', 'offset'),
                                     (tname+'_sequence', 'hf_index', ectx.eth_type[tname]['tree'])))
      elif (ectx.NPer()):
        body = ectx.eth_fn_call('dissect_per_sequence' + ectx.pvp(), ret='offset',
                                par=(('tvb', 'offset', 'pinfo', 'tree'),
                                     ('hf_index', 'item', 'private_data'),
                                     (ectx.eth_type[tname]['tree'], tname+'_sequence'+ectx.pvp(), '"'+tname+'"')))
      elif (ectx.OPer()):
        body = ectx.eth_fn_call('dissect_per_sequence' + ectx.pvp(), ret='offset',
                                par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                     (ectx.eth_type[tname]['tree'], tname+'_sequence'+ectx.pvp())))
      else:
        body = '#error Can not decode %s' % (tname)
      out += ectx.eth_type_fn_body(tname, body)
      out += ectx.eth_type_fn_ftr(tname)
      return out

#--- SetType ------------------------------------------------------------------
class SetType(SqType):
  def eth_reg_sub(self, ident, ectx):
    for e in (self.elt_list):
      e.val.eth_reg(ident, ectx, parent=ident)
    if hasattr(self, 'ext_list'):
      for e in (self.ext_list):
        e.val.eth_reg(ident, ectx, parent=ident)

  def eth_need_tree(self):
    return True

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_SET')

  def eth_type_fn(self, proto, tname, ectx):
    out = "static per_set_new_t %s_sequence_new[] = {\n" % (tname)
    fname = ectx.eth_type[tname]['ref'][0]
    if hasattr(self, 'ext_list'):
      ext = 'ASN1_EXTENSION_ROOT'
    else:
      ext = 'ASN1_NO_EXTENSIONS'
    for e in (self.elt_list):
      f = fname + '/' + e.val.name
      out += self.out_item(f, e.val, e.optional, ext, ectx)
    if hasattr(self, 'ext_list'):
      for e in (self.ext_list):
        f = fname + '/' + e.val.name
        out += self.out_item(f, e.val, e.optional, 'ASN1_NOT_EXTENSION_ROOT', ectx)
    out += "  { NULL, 0, 0, NULL }\n};\n"
    out += ectx.eth_type_fn_hdr(tname)
    body = "  offset = dissect_per_set_new(tvb, offset, pinfo, tree,\n" \
           "                               hf_index, item, private_data,\n"
    body += '                               %s, %s_sequence_new, "%s");\n' \
           % (ectx.eth_type[tname]['tree'], tname, tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

#--- ChoiceType ---------------------------------------------------------------
class ChoiceType (Type):
    def to_python (self, ctx):
        # name, tag (None for no tag, EXPLICIT() for explicit), typ)
        # or '' + (1,) for optional
        if self.__dict__.has_key('ext_list'):
          return "%sasn1.CHOICE ([%s], ext=[%s])" % (ctx.spaces (), 
                                 self.elts_to_py (self.elt_list, ctx),
                                 self.elts_to_py (self.ext_list, ctx))
        else:
          return "%sasn1.CHOICE ([%s])" % (ctx.spaces (), self.elts_to_py (self.elt_list, ctx))
    def elts_to_py (self, list, ctx):
        ctx.indent ()
        def elt_to_py (nt):
            assert (nt.type == 'named_type')
            tagstr = 'None'
            if hasattr (nt, 'ident'):
                identstr = nt.ident
            else:
                if hasattr (nt.typ, 'val'):
                    identstr = nt.typ.val # XXX, making up name
                elif hasattr (nt.typ, 'name'):
                    identstr = nt.typ.name
                else:
                    identstr = ctx.make_new_name ()

            if hasattr (nt.typ, 'type') and nt.typ.type == 'tag': # ugh
                tagstr = mk_tag_str (ctx,nt.typ.tag.cls,
                                     nt.typ.tag.tag_typ,nt.typ.tag.num)
        

                nt = nt.typ
            return "('%s',%s,%s)" % (identstr, tagstr,
                                      nt.typ.to_python (ctx))
        indentstr = ",\n" + ctx.spaces ()
        rv =  indentstr.join ([elt_to_py (e) for e in list])
        ctx.outdent ()
        return rv

    def eth_reg_sub(self, ident, ectx):
        #print "eth_reg_sub(ident='%s')" % (ident)
        for e in (self.elt_list):
            e.eth_reg(ident, ectx, parent=ident)
        if hasattr(self, 'ext_list'):
            for e in (self.ext_list):
                e.eth_reg(ident, ectx, parent=ident)

    def eth_ftype(self):
      return ('FT_UINT32', 'BASE_DEC')

    def eth_strings(self):
      return '$$'

    def eth_need_tree(self):
      return True

    def eth_has_vals(self):
      return True

    def GetTTag(self, ectx):
      lst = self.elt_list
      cls = '-1/*choice*/'
      if hasattr(self, 'ext_list'):
        lst.extend(self.ext_list)
      if (len(lst) > 0):
        cls = lst[0].GetTag(ectx)[0]
      for e in (lst):
        if (e.GetTag(ectx)[0] != cls):
          cls = '-1/*choice*/'
      return (cls, '-1/*choice*/')

    def IndetermTag(self, ectx):
      #print "Choice IndetermTag()=%s" % (str(not self.HasOwnTag()))
      return not self.HasOwnTag()

    def eth_type_vals(self, proto, tname, ectx):
      out = '\n'
      tagval = False
      if (ectx.Ber()):
        lst = self.elt_list
        if hasattr(self, 'ext_list'):
          lst.extend(self.ext_list)
        if (len(lst) > 0):
          t = lst[0].GetTag(ectx)[0]
          tagval = True
        if (t == 'BER_CLASS_UNI'):
          tagval = False
        for e in (lst):
          if (e.GetTag(ectx)[0] != t):
            tagval = False
      vals = []
      cnt = 0
      for e in (self.elt_list):
        if (tagval): val = e.GetTag(ectx)[1]
        else: val = str(cnt)
        vals.append((val, e.name))
        cnt += 1
      if hasattr(self, 'ext_list'):
        for e in (self.ext_list):
          if (tagval): val = e.GetTag(ectx)[1]
          else: val = str(cnt)
          vals.append((val, e.name))
          cnt += 1
      out += ectx.eth_vals(tname, vals)
      return out

    def eth_type_fn(self, proto, tname, ectx):
      def out_item(val, e, ext, ectx):
        f = fname + '/' + e.name
        ef = ectx.field[f]['ethname']
        efd = ef
        if (ectx.field[f]['impl']):
          efd += '_impl'
        if (ectx.encoding == 'ber'):
          opt = ''
          if (not e.HasOwnTag()):
            opt = 'BER_FLAGS_NOOWNTAG'
          elif (e.tag.mode == 'IMPLICIT'):
            if (opt): opt += '|'
            opt += 'BER_FLAGS_IMPLTAG'
          if (not opt): opt = '0'
        if (ectx.OBer()):
          (tc, tn) = e.GetTag(ectx)
          out = '  { %3s, %-13s, %s, %s, dissect_%s },\n' \
                % (val, tc, tn, opt, efd)
        elif (ectx.NPer()):
          out = '  { %3s, &%-30s, %-23s, dissect_%s_%s },\n' \
                % (val, ef, ext, ectx.eth_type[ectx.eth_hf[ef]['ethtype']]['proto'], ectx.eth_hf[ef]['ethtype'])
        elif (ectx.OPer()):
          out = '  { %3s, %-30s, %-23s, dissect_%s },\n' \
                % (val, '"'+e.name+'"', ext, efd)
        else:
          out = ''
        return out   
      # end out_item()
      fname = ectx.eth_type[tname]['ref'][0]
      out = '\n'
      tagval = False
      if (ectx.Ber()):
        lst = self.elt_list
        if hasattr(self, 'ext_list'):
          lst.extend(self.ext_list)
        if (len(lst) > 0):
          t = lst[0].GetTag(ectx)[0]
          tagval = True
        if (t == 'BER_CLASS_UNI'):
          tagval = False
        for e in (lst):
          if (e.GetTag(ectx)[0] != t):
            tagval = False
      if (ectx.encoding == 'ber'):
        out += "static ber_choice %s_choice[] = {\n" % (tname)
      else:
        out += "static per_choice%s_t %s_choice%s[] = {\n" % (ectx.pvp(), tname, ectx.pvp())
      cnt = 0
      if hasattr(self, 'ext_list'):
        ext = 'ASN1_EXTENSION_ROOT'
      else:
        ext = 'ASN1_NO_EXTENSIONS'
      for e in (self.elt_list):
        if (tagval): val = e.GetTag(ectx)[1]
        else: val = str(cnt)
        out += out_item(val, e, ext, ectx)
        cnt += 1
      if hasattr(self, 'ext_list'):
        for e in (self.ext_list):
          if (tagval): val = e.GetTag(ectx)[1]
          else: val = str(cnt)
          out += out_item(val, e, 'ASN1_NOT_EXTENSION_ROOT', ectx)
          cnt += 1
      if (ectx.encoding == 'ber'):
        out += "  { 0, 0, 0, 0, NULL }\n};\n"
      else:
        out += "  { 0, NULL, 0, NULL }\n};\n"
      out += ectx.eth_type_fn_hdr(tname)
      if (ectx.Ber()):
        body = ectx.eth_fn_call('dissect_ber_choice' + ectx.pvp(), ret='offset',
                                par=(('pinfo', 'tree', 'tvb', 'offset'),
                                     (tname+'_choice', 'hf_index', ectx.eth_type[tname]['tree'])))
      elif (ectx.NPer()):
        body = ectx.eth_fn_call('dissect_per_choice' + ectx.pvp(), ret='offset',
                                par=(('tvb', 'offset', 'pinfo', 'tree'),
                                     ('hf_index', 'item', 'private_data'),
                                     (ectx.eth_type[tname]['tree'], tname+'_choice'+ectx.pvp(), '"'+tname+'"'),
                                     ('NULL',)))
      elif (ectx.OPer()):
        body = ectx.eth_fn_call('dissect_per_choice' + ectx.pvp(), ret='offset',
                                par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                     (ectx.eth_type[tname]['tree'], tname+'_choice'+ectx.pvp(), '"'+tname+'"'),
                                     ('NULL',)))
      else:
        body = '#error Can not decode %s' % (tname)
      out += ectx.eth_type_fn_body(tname, body)
      out += ectx.eth_type_fn_ftr(tname)
      return out

   
#--- EnumeratedType -----------------------------------------------------------
class EnumeratedType (Type):
  def to_python (self, ctx):
    def strify_one (named_num):
      return "%s=%s" % (named_num.ident, named_num.val)
    return "asn1.ENUM(%s)" % ",".join (map (strify_one, self.val))

  def eth_ftype(self):
    return ('FT_UINT32', 'BASE_DEC')

  def eth_strings(self):
    return '$$'

  def eth_has_vals(self):
    return True

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_ENUMERATED')

  def eth_type_vals(self, proto, tname, ectx):
    out = '\n'
    vals = []
    lastv = 0
    used = {}
    maxv = 0
    for e in (self.val):
      if e.type == 'NamedNumber':
        used[int(e.val)] = True
    for e in (self.val):
      if e.type == 'NamedNumber':
        val = int(e.val)
      else:
        while used.has_key(lastv):
          lastv += 1
        val = lastv
        used[val] = True
      vals.append((val, e.ident))
      if val > maxv:
        maxv = val
    if self.ext is not None:
      for e in (self.ext):
        if e.type == 'NamedNumber':
          used[int(e.val)] = True
      for e in (self.ext):
        if e.type == 'NamedNumber':
          val = int(e.val)
        else:
          while used.has_key(lastv):
            lastv += 1
          val = lastv
        vals.append((val, e.ident))
        if val > maxv:
          maxv = val
    out += ectx.eth_vals(tname, vals)
    return out

  def eth_type_fn(self, proto, tname, ectx):
    fname = ectx.eth_type[tname]['ref'][0]
    out = '\n'
    if self.ext is None:
      ext = 'FALSE'
    else:
      ext = 'TRUE'
    out += ectx.eth_type_fn_hdr(tname)
    if (ectx.Ber()):
      body = ectx.eth_fn_call('dissect_ber_integer' + ectx.pvp(), ret='offset',
                              par=(('pinfo', 'tree', 'tvb', 'offset', 'hf_index', 'NULL'),))
    else:
      body = "  offset = dissect_per_constrained_integer_new(tvb, offset, pinfo, tree,\n"
      body += "                                               %s, %s, %s,\n" \
             % (0, maxv, ext)
      body += "                                               NULL);\n"
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

class Literal (Node):
    def to_python (self, ctx):
        return self.val

#--- NullType -----------------------------------------------------------------
class NullType (Type):
  def to_python (self, ctx):
    return 'asn1.NULL'

  def eth_tname(self):
    return 'NULL'

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_NULL')

  def eth_type_fn(self, proto, tname, ectx):
    out = ectx.eth_type_fn_hdr(tname)
    if (ectx.new):
      body = ectx.eth_fn_call('dissect_per_null' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree'),
                                   ('hf_index', 'item', 'NULL')))
    else:
      body = '  { proto_item *ti_tmp;\n';
      body += ectx.eth_fn_call('proto_tree_add_item', 'ti_tmp',
                              par=(('tree', 'hf_index', 'tvb', 'offset>>8', '0', 'FALSE'),))
      body += ectx.eth_fn_call('proto_item_append_text',
                              par=(('ti_tmp', '": NULL"'),))
      body += '  }\n';
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

#--- RealType -----------------------------------------------------------------
class RealType (Type):
  def to_python (self, ctx):
    return 'asn1.REAL'

  def eth_tname(self):
    return 'REAL'

  def eth_type_fn(self, proto, tname, ectx):
    out = ectx.eth_type_fn_hdr(tname)
    #out += "  offset = dissect_per_real_new(tvb, offset, pinfo, tree,\n" \
    #       "                                hf_index, item, NULL);\n"
    #
    # XXX - "PER_NOT_DECODED_YET()" or "BER_NOT_DECODED_YET()"?
    #
    body = 'NOT_DECODED_YET("%s");\n' % (tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

#--- BooleanType --------------------------------------------------------------
class BooleanType (Type):
  def to_python (self, ctx):
    return 'asn1.BOOLEAN'

  def eth_tname(self):
    return 'BOOLEAN'

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_BOOLEAN')

  def eth_ftype(self):
    return ('FT_BOOLEAN', '8')

  def eth_type_fn(self, proto, tname, ectx):
    out = ectx.eth_type_fn_hdr(tname)
    if (ectx.Ber()):
      body = ectx.eth_fn_call('dissect_ber_boolean' + ectx.pvp(), ret='offset',
                              par=(('pinfo', 'tree', 'tvb', 'offset', 'hf_index'),))
    elif (ectx.NPer()):
      body = ectx.eth_fn_call('dissect_per_boolean' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree'),
                                   ('hf_index', 'item', 'NULL')))
    elif (ectx.OPer()):
      body = ectx.eth_fn_call('dissect_per_boolean' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                   ('NULL', 'NULL')))
    else:
      body = '#error Can not decode %s' % (tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

#--- OctetStringType ----------------------------------------------------------
class OctetStringType (Type):
  def to_python (self, ctx):
    return 'asn1.OCTSTRING'

  def eth_tname(self):
    if not self.HasConstraint():
      return 'OCTET_STRING'
    elif self.constr.type == 'Size' and (self.constr.subtype.type == 'SingleValue' or self.constr.subtype.type == 'ValueRange'):
      return 'OCTET_STRING' + '_' + self.constr.eth_constrname()
    else:
      return '#' + self.type + '_' + str(id(self))

  def eth_ftype(self):
    return ('FT_BYTES', 'BASE_HEX')

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_OCTETSTRING')

  def eth_type_fn(self, proto, tname, ectx):
    out = ectx.eth_type_fn_hdr(tname)
    (minv, maxv, ext) = self.eth_get_size_constr()
    if (ectx.OBer()):
      body = ectx.eth_fn_call('dissect_ber_octet_string' + ectx.pvp(), ret='offset',
                              par=(('implicit_tag', 'pinfo', 'tree', 'tvb', 'offset', 'hf_index'),
                                   ('NULL',)))
    elif (ectx.NPer()):
      body = ectx.eth_fn_call('dissect_per_octet_string' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree'),
                                   ('hf_index', 'item', 'private_data'),
                                   (minv, maxv, ext),
                                   ('NULL', 'NULL')))
    elif (ectx.OPer()):
      body = ectx.eth_fn_call('dissect_per_octet_string' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                   (minv, maxv),
                                   ('NULL', 'NULL')))
    else:
      body = '#error Can not decode %s' % (tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

#--- CharacterStringType ------------------------------------------------------
class CharacterStringType (Type):
  def eth_tname(self):
    if not self.HasConstraint():
      return self.eth_tsname()
    elif self.constr.type == 'Size' and (self.constr.subtype.type == 'SingleValue' or self.constr.subtype.type == 'ValueRange'):
      return self.eth_tsname() + '_' + self.constr.eth_constrname()
    else:
      return '#' + self.type + '_' + str(id(self))

  def eth_ftype(self):
    return ('FT_STRING', 'BASE_NONE')

class RestrictedCharacterStringType (CharacterStringType):
  def to_python (self, ctx):
    return 'asn1.' + self.eth_tsname()

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_' + self.eth_tsname())

  def eth_type_fn(self, proto, tname, ectx):
    out = ectx.eth_type_fn_hdr(tname)
    (minv, maxv, ext) = self.eth_get_size_constr()
    if (ectx.Ber()):
      body = ectx.eth_fn_call('dissect_ber_restricted_string' + ectx.pvp(), ret='offset',
                              par=(('implicit_tag', self.GetTag(ectx)[1]),
                                   ('pinfo', 'tree', 'tvb', 'offset', 'hf_index'),
                                   ('NULL',)))
    elif (ectx.NPer()):
      body = ectx.eth_fn_call('dissect_per_' + self.eth_tsname() + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree'),
                                   ('hf_index', 'item', 'private_data'),
                                   (minv, maxv, ext),
                                   ('NULL', 'NULL')))
    elif (ectx.OPer()):
      body = ectx.eth_fn_call('dissect_per_'  + self.eth_tsname() + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                   (minv, maxv)))
    else:
      body = '#error Can not decode %s' % (tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

class BMPStringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'BMPString'

class GeneralStringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'GeneralString'

class GraphicStringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'GraphicString'

class IA5StringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'IA5String'

class NumericStringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'NumericString'

class PrintableStringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'PrintableString'

class TeletexStringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'TeletexString'

class T61StringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'T61String'
  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_Teletext')

class UniversalStringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'UniversalString'

class UTF8StringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'UTF8String'

class VideotexStringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'VideotexString'

class VisibleStringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'VisibleString'

class ISO646StringType (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'ISO646String'
  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_VisibleString')

class UnrestrictedCharacterStringType (CharacterStringType):
  def to_python (self, ctx):
    return 'asn1.UnrestrictedCharacterString'
  def eth_tsname(self):
    return 'CHARACTER_STRING'

#--- UsefulType ---------------------------------------------------------------
class GeneralizedTime (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'GeneralizedTime'

  def eth_type_fn(self, proto, tname, ectx):
    if (ectx.Ber()):
      out = ectx.eth_type_fn_hdr(tname)
      body = ectx.eth_fn_call('dissect_ber_generalized_time' + ectx.pvp(), ret='offset',
                              par=(('pinfo', 'tree', 'tvb', 'offset', 'hf_index'),))
      out += ectx.eth_type_fn_body(tname, body)
      out += ectx.eth_type_fn_ftr(tname)
      return out
    else:
      return RestrictedCharacterStringType(self, proto, tname, ectx)

class UTCTime (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'UTCTime'

class ObjectDescriptor (RestrictedCharacterStringType):
  def eth_tsname(self):
    return 'ObjectDescriptor'


#--- ObjectIdentifierType -----------------------------------------------------
class ObjectIdentifierType (Type):
  def to_python (self, ctx):
    return 'asn1.OBJECT_IDENTIFIER'

  def eth_tname(self):
    return 'OBJECT_IDENTIFIER'

  def eth_ftype(self):
    return ('FT_STRING', 'BASE_NONE')

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_OID')

  def eth_type_fn(self, proto, tname, ectx):
    out = ectx.eth_type_fn_hdr(tname)
    if (ectx.OBer()):
      body = ectx.eth_fn_call('dissect_ber_object_identifier' + ectx.pvp(), ret='offset',
                              par=(('implicit_tag', 'pinfo', 'tree', 'tvb', 'offset'),
                                   ('hf_index', 'NULL')))
    elif (ectx.NPer()):
      body = ectx.eth_fn_call('dissect_per_object_identifier' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree'),
                                   ('hf_index', 'item', 'NULL')))
    elif (ectx.OPer()):
      body = ectx.eth_fn_call('dissect_per_object_identifier' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                   ('NULL',)))
    else:
      body = '#error Can not decode %s' % (tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

#--- ObjectIdentifierValue ----------------------------------------------------
class ObjectIdentifierValue (Value):
  def get_num(self, path, val):
    return str(oid_names.get(path + '/' + val, val))

  def to_str(self):
    out = ''
    path = ''
    first = True
    sep = ''
    for v in self.comp_list:
      if isinstance(v, Node) and (v.type == 'name_and_number'):
        vstr = v.number
      elif v.isdigit():
        vstr = v
      else:
        vstr = self.get_num(path, v)
      if first:
        if vstr.isdigit():
          out += '"' + vstr
        else:
          out += vstr + '"'
      else:
       out += sep + vstr
      path += sep + vstr
      first = False
      sep = '.'
    out += '"'
    return out

  def get_dep(self):
    v = self.comp_list[0]
    if isinstance(v, Node) and (v.type == 'name_and_number'):
      return None
    elif v.isdigit():
      return None
    else:
      vstr = self.get_num('', v)
    if vstr.isdigit():
      return None
    else:
      return vstr

class NamedNumber (Node):
    def to_python (self, ctx):
        return "('%s',%s)" % (self.ident, self.val)

class NamedNumListBase(Node):
    def to_python (self, ctx):
        return "asn1.%s_class ([%s])" % (self.asn1_typ,",".join (
            map (lambda x: x.to_python (ctx), self.named_list)))

#--- IntegerType --------------------------------------------------------------
class IntegerType (Type):
  def to_python (self, ctx):
        return "asn1.INTEGER_class ([%s])" % (",".join (
            map (lambda x: x.to_python (ctx), self.named_list)))

  def eth_tname(self):
    if self.named_list:
      return Type.eth_tname(self)
    if not self.HasConstraint():
      return 'INTEGER'
    elif self.constr.type == 'SingleValue' or self.constr.type == 'ValueRange':
      return 'INTEGER' + '_' + self.constr.eth_constrname()
    else:
      return 'INTEGER' + '_' + self.constr.eth_tname()

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_INTEGER')

  def eth_ftype(self):
    if self.HasConstraint():
      if self.constr.type == 'SingleValue':
        if self.constr.subtype >= 0:
          return ('FT_UINT32', 'BASE_DEC')
      elif self.constr.type == 'ValueRange':
        if self.constr.subtype[0] >= 0:
          return ('FT_UINT32', 'BASE_DEC')
    return ('FT_INT32', 'BASE_DEC')

  def eth_strings(self):
    if (self.named_list):
      return '$$'
    else:
      return 'NULL'

  def eth_has_vals(self):
    if (self.named_list):
      return True
    else:
      return False

  def eth_type_vals(self, proto, tname, ectx):
    if not self.eth_has_vals(): return ''
    out = '\n'
    vals = []
    for e in (self.named_list):
      vals.append((int(e.val), e.ident))
    out += ectx.eth_vals(tname, vals)
    return out

  def eth_type_fn(self, proto, tname, ectx):
    out = '\n'
    out += ectx.eth_type_fn_hdr(tname)
    if (ectx.Ber()):
      body = ectx.eth_fn_call('dissect_ber_integer' + ectx.pvp(), ret='offset',
                              par=(('pinfo', 'tree', 'tvb', 'offset', 'hf_index', 'NULL'),))
    elif (not self.HasConstraint()):
      if (ectx.New()):
        body = ectx.eth_fn_call('dissect_per_integer' + ectx.pvp(), ret='offset',
                                par=(('tvb', 'offset', 'pinfo', 'tree'),
                                     ('hf_index', 'item', 'private_data'),
                                     ('NULL',)))
      else:
        body = ectx.eth_fn_call('dissect_per_integer' + ectx.pvp(), ret='offset',
                                par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                     ('NULL', 'NULL')))
    elif ((self.constr.type == 'SingleValue') or (self.constr.type == 'ValueRange')):
      if self.constr.type == 'SingleValue':
        minv = self.constr.subtype
        maxv = self.constr.subtype
      else:
        minv = self.constr.subtype[0]
        maxv = self.constr.subtype[1]
      if str(minv).isdigit(): minv += 'U'
      if str(maxv).isdigit(): maxv += 'U'
      if hasattr(self.constr, 'ext') and self.constr.ext:
        ext = 'TRUE'
      else:
        ext = 'FALSE'
      if (ectx.New()):
        body = ectx.eth_fn_call('dissect_per_constrained_integer' + ectx.pvp(), ret='offset',
                                par=(('tvb', 'offset', 'pinfo', 'tree'),
                                     ('hf_index', 'item', 'private_data'),
                                     (minv, maxv, ext),
                                     ('NULL',)))
      else:
        body = ectx.eth_fn_call('dissect_per_constrained_integer' + ectx.pvp(), ret='offset',
                                par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                     (minv, maxv, 'NULL', 'NULL', ext)))
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out

#--- BitStringType ------------------------------------------------------------
class BitStringType (Type):
  def to_python (self, ctx):
        return "asn1.BITSTRING_class ([%s])" % (",".join (
            map (lambda x: x.to_python (ctx), self.named_list)))

  def eth_tname(self):
    if self.named_list:
      return Type.eth_tname(self)
    elif not self.HasConstraint():
      return 'BIT_STRING'
    elif self.constr.type == 'Size' and (self.constr.subtype.type == 'SingleValue' or self.constr.subtype.type == 'ValueRange'):
      return 'BIT_STRING' + '_' + self.constr.eth_constrname()
    else:
      return '#' + self.type + '_' + str(id(self))

  def GetTTag(self, ectx):
    return ('BER_CLASS_UNI', 'BER_UNI_TAG_BITSTRING')

  def eth_ftype(self):
    return ('FT_BYTES', 'BASE_HEX')

  def eth_need_tree(self):
    return self.named_list

  def eth_named_bits(self):
    bits = []
    if (self.named_list):
      for e in (self.named_list):
        bits.append((int(e.val), e.ident))
    return bits

  def eth_type_fn(self, proto, tname, ectx):
    out = ''
    bits = []
    bitsp = 'NULL'
    if (self.named_list):
      for e in (self.named_list):
        bits.append((int(e.val), e.ident))
      out += ectx.eth_bits(tname, bits)
      bitsp = tname + '_bits'
    out += ectx.eth_type_fn_hdr(tname)
    (minv, maxv, ext) = self.eth_get_size_constr()
    tree = '-1'
    if (ectx.eth_type[tname]['tree']):
      tree = ectx.eth_type[tname]['tree']
    if (ectx.OBer()):
      body = ectx.eth_fn_call('dissect_ber_bitstring' + ectx.pvp(), ret='offset',
                              par=(('implicit_tag', 'pinfo', 'tree', 'tvb', 'offset'),
                                   (bitsp, 'hf_index', tree),
                                   ('NULL',)))
    elif (ectx.NPer()):
      body = ectx.eth_fn_call('dissect_per_bit_string' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree'),
                                   ('hf_index', 'item', 'private_data'),
                                   (minv, maxv, ext),
                                   ('NULL', 'NULL')))
    elif (ectx.OPer()):
      body = ectx.eth_fn_call('dissect_per_bit_string' + ectx.pvp(), ret='offset',
                              par=(('tvb', 'offset', 'pinfo', 'tree', 'hf_index'),
                                   (minv, maxv)))
    else:
      body = '#error Can not decode %s' % (tname)
    out += ectx.eth_type_fn_body(tname, body)
    out += ectx.eth_type_fn_ftr(tname)
    return out


#==============================================================================
    
def p_module_list_1 (t):
    'module_list : module_list module_def'
    t[0] = t[1] + [t[2]]

def p_module_list_2 (t):
    'module_list : module_def'
    t[0] = [t[1]]


#--- ITU-T Recommendation X.680 -----------------------------------------------


# 11 ASN.1 lexical items --------------------------------------------------------

# 11.2 Type references
def p_type_ref (t):
    'type_ref : UCASE_IDENT'
    t[0] = Type_Ref(val=t[1])

# 11.4 Value references
def p_valuereference (t):
    'valuereference : LCASE_IDENT'
    t[0] = t[1]


# 12 Module definition --------------------------------------------------------

# 12.1
def p_module_def (t):
    'module_def : module_ident DEFINITIONS TagDefault ASSIGNMENT BEGIN module_body END'
    t[0] = Module (ident = t[1], tag_def = t[3], body = t[6])

def p_TagDefault_1 (t):
    '''TagDefault : EXPLICIT TAGS
    | IMPLICIT TAGS
    | AUTOMATIC TAGS'''
    t[0] = Default_Tags (dfl_tag = t[1])

def p_TagDefault_2 (t):
    'TagDefault : '
    # 12.2 The "TagDefault" is taken as EXPLICIT TAGS if it is "empty".
    t[0] = Default_Tags (dfl_tag = 'EXPLICIT') 

def p_module_ident (t):
    'module_ident : type_ref assigned_ident' # name, oid
    # XXX coerce type_ref to module_ref
    t [0] = Node('module_ident', val = t[1].val, ident = t[2])


# XXX originally we had both type_ref and module_ref, but that caused
# a reduce/reduce conflict (because both were UCASE_IDENT).  Presumably
# this didn't cause a problem in the original ESNACC grammar because it
# was LALR(1) and PLY is (as of 1.1) only SLR.

#def p_module_ref (t):
#    'module_ref : UCASE_IDENT'
#    t[0] = t[1]

def p_assigned_ident_1 (t):
    'assigned_ident : ObjectIdentifierValue'
    t[0] = t[1]

def p_assigned_ident_2 (t):
    'assigned_ident : LCASE_IDENT'
    t[0] = t[1]

def p_assigned_ident_3 (t):
    'assigned_ident : '
    pass

def p_module_body_1 (t):
    'module_body : exports Imports AssignmentList'
    t[0] = Module_Body (exports = t[1], imports = t[2], assign_list = t[3])

def p_module_body_2 (t):
    'module_body : '
    t[0] = Node ('module_body', exports = [], imports = [],
                 assign_list = [])

def p_exports_1 (t):
    'exports : EXPORTS syms_exported SEMICOLON'
    t[0] = t[2]

def p_exports_2 (t):
    'exports : '
    t[0] = []

def p_syms_exported_1 (t):
    'syms_exported : exp_sym_list'
    t[0] = t[1]

def p_syms_exported_2 (t):
    'syms_exported : '
    t[0] = []

def p_exp_sym_list_1 (t):
    'exp_sym_list : Symbol'
    t[0] = [t[1]]

def p_exp_sym_list_2 (t):
    'exp_sym_list : exp_sym_list COMMA Symbol'
    t[0] = t[1] + [t[3]]
    

def p_Imports_1(t):
    'Imports : IMPORTS SymbolsImported SEMICOLON'
    t[0] = t[2]

def p_Imports_2 (t):
    'Imports : '
    t[0] = []

def p_SymbolsImported_1(t):
    'SymbolsImported : '
    t[0] = []

def p_SymbolsImported_2 (t):
    'SymbolsImported : SymbolsFromModuleList'
    t[0] = t[1]

def p_SymbolsFromModuleList_1 (t):
    'SymbolsFromModuleList : SymbolsFromModuleList SymbolsFromModule'
    t[0] = t[1] + [t[2]]

def p_SymbolsFromModuleList_2 (t):
    'SymbolsFromModuleList : SymbolsFromModule'
    t[0] = [t[1]]

def p_SymbolsFromModule (t):
    'SymbolsFromModule : SymbolList FROM module_ident'
    t[0] = Node ('SymbolList', symbol_list = t[1], module = t[3])

def p_SymbolList_1 (t):
    'SymbolList : Symbol'
    t[0] = [t[1]]

def p_SymbolList_2 (t):
    'SymbolList : SymbolList COMMA Symbol'
    t[0] = t[1] + [t[3]]

def p_Symbol (t):
    '''Symbol : type_ref
              | ParameterizedReference
              | identifier''' # XXX omit DefinedMacroName
    t[0] = t[1]

def p_Reference (t):
    '''Reference : type_ref
                 | valuereference'''
    t[0] = t[1]

def p_AssignmentList_1 (t):
    'AssignmentList : AssignmentList Assignment'
    t[0] = t[1] + [t[2]]

def p_AssignmentList_2 (t):
    'AssignmentList : Assignment SEMICOLON'
    t[0] = [t[1]]

def p_AssignmentList_3 (t):
    'AssignmentList : Assignment'
    t[0] = [t[1]]

def p_Assignment (t):
    '''Assignment : TypeAssignment
                  | ValueAssignment
                  | pyquote
                  | ParameterizedTypeAssignment'''
    t[0] = t[1]

def p_pyquote (t):
    '''pyquote : PYQUOTE'''
    t[0] = PyQuote (val = t[1])


# 13 Referencing type and value definitions -----------------------------------

# 13.1
def p_DefinedType (t): 
  '''DefinedType : ext_type_ref
  | type_ref
  | ParameterizedType'''
  t[0] = t[1]

def p_DefinedValue(t):
  '''DefinedValue : ext_val_ref
                  | identifier'''
  t[0] = t[1]


# 15 Assigning types and values -----------------------------------------------

# 15.1
def p_TypeAssignment (t):
  'TypeAssignment : UCASE_IDENT ASSIGNMENT Type'
  t[0] = t[3]
  t[0].SetName(t[1])

# 15.2
def p_ValueAssignment (t):
  'ValueAssignment : identifier Type ASSIGNMENT Value'
  t[0] = value_assign (ident = t[1], typ = t[2], val = t[4])


# 16 Definition of types and values -------------------------------------------

# 16.1
def p_Type (t):
  '''Type : BuiltinType
  | ReferencedType
  | ConstrainedType'''
  t[0] = t[1]

# 16.2
def p_BuiltinType (t):
  '''BuiltinType : BitStringType
                 | BooleanType
                 | CharacterStringType
                 | ChoiceType
                 | EnumeratedType
                 | IntegerType
                 | NullType
                 | ObjectIdentifierType
                 | OctetStringType
                 | RealType
                 | SequenceType
                 | SequenceOfType
                 | SetType
                 | SetOfType
                 | selection_type
                 | any_type
                 | TaggedType'''
  t[0] = t[1]

# 16.3
def p_ReferencedType (t):
  '''ReferencedType : DefinedType
                    | UsefulType'''
  t[0] = t[1]

def p_ext_type_ref (t):
    'ext_type_ref : type_ref DOT type_ref'
    # XXX coerce 1st type_ref to module_ref
    t[0] = Node ('ext_type_ref', module = t[1], typ = t[3])

# 16.5
def p_NamedType (t):
  'NamedType : identifier Type'
  t[0] = t[2]
  t[0].SetName (t[1]) 

# 16.7
def p_Value (t):
  '''Value : BuiltinValue
           | ReferencedValue'''
  t[0] = t[1]

# 16.9
def p_BuiltinValue (t):
  '''BuiltinValue : BooleanValue
                  | ObjectIdentifierValue
                  | special_real_val
                  | SignedNumber
                  | hex_string
                  | binary_string
                  | char_string''' # XXX we don't support {data} here
  t[0] = t[1]

# 16.11
def p_ReferencedValue (t):
  '''ReferencedValue : DefinedValue'''
  t[0] = t[1]

# 16.13
#def p_NamedValue (t):
#  'NamedValue : identifier Value'
#  t[0] = Node ('NamedValue', ident = t[1], value = t[2])


# 17 Notation for the boolean type --------------------------------------------

# 17.1
def p_BooleanType (t):
  'BooleanType : BOOLEAN'
  t[0] = BooleanType ()

# 17.2
def p_BooleanValue (t):
  '''BooleanValue : TRUE
                  | FALSE'''
  t[0] = t[1]


# 18 Notation for the integer type --------------------------------------------

# 18.1
def p_IntegerType_1 (t):
  'IntegerType : INTEGER'
  t[0] = IntegerType (named_list = None)

def p_IntegerType_2 (t):
  'IntegerType : INTEGER LBRACE NamedNumberList RBRACE'
  t[0] = IntegerType (named_list = t[3])

def p_NamedNumberList_1 (t):
  'NamedNumberList : NamedNumber'
  t[0] = [t[1]]

def p_NamedNumberList_2 (t):
  'NamedNumberList : NamedNumberList COMMA NamedNumber'
  t[0] = t[1] + [t[3]]

def p_NamedNumber (t):
  '''NamedNumber : identifier LPAREN SignedNumber RPAREN
                 | identifier LPAREN DefinedValue RPAREN'''
  t[0] = NamedNumber (ident = t[1], val = t[3])

def p_SignedNumber_1 (t):
  'SignedNumber : NUMBER'
  t[0] = t [1]

def p_SignedNumber_2 (t):
  'SignedNumber : MINUS NUMBER'
  t[0] = '-' + t[2]


# 19 Notation for the enumerated type -----------------------------------------

# 19.1
def p_EnumeratedType (t):
    'EnumeratedType : ENUMERATED LBRACE Enumerations RBRACE'
    t[0] = EnumeratedType (val = t[3]['val'], ext = t[3]['ext'])

def p_Enumerations_1 (t):
    'Enumerations : Enumeration'
    t[0] = { 'val' : t[1], 'ext' : None }

def p_Enumerations_2 (t):
    'Enumerations : Enumeration COMMA ELLIPSIS ExceptionSpec'
    t[0] = { 'val' : t[1], 'ext' : [] }

def p_Enumerations_3 (t):
    'Enumerations : Enumeration COMMA ELLIPSIS ExceptionSpec COMMA Enumeration'
    t[0] = { 'val' : t[1], 'ext' : t[6] }

def p_Enumeration_1 (t):
    'Enumeration : EnumerationItem'
    t[0] = [t[1]]

def p_Enumeration_2 (t):
    'Enumeration : Enumeration COMMA EnumerationItem'
    t[0] = t[1] + [t[3]]

def p_EnumerationItem (t):
    '''EnumerationItem : Identifier
                       | NamedNumber'''
    t[0] = t[1]

def p_Identifier (t):
    'Identifier : identifier'
    t[0] = Node ('Identifier', ident = t[1])


# 20 Notation for the real type -----------------------------------------------

# 20.1
def p_RealType (t):
    'RealType : REAL'
    t[0] = RealType ()

# 21 Notation for the bitstring type ------------------------------------------

# 21.1
def p_BitStringType_1 (t):
    'BitStringType : BIT STRING'
    t[0] = BitStringType (named_list = None)

def p_BitStringType_2 (t):
    'BitStringType : BIT STRING LBRACE NamedBitList RBRACE'
    t[0] = BitStringType (named_list = t[4])

def p_NamedBitList_1 (t):
    'NamedBitList : NamedBit'
    t[0] = [t[1]]

def p_NamedBitList_2 (t):
    'NamedBitList : NamedBitList COMMA NamedBit'
    t[0] = t[1] + [t[3]]

def p_NamedBit (t):
    '''NamedBit : identifier LPAREN NUMBER RPAREN
                | identifier LPAREN DefinedValue RPAREN'''
    t[0] = NamedNumber (ident = t[1], val = t[3])


# 22 Notation for the octetstring type ----------------------------------------

# 22.1
def p_OctetStringType (t):
    'OctetStringType : OCTET STRING'
    t[0] = OctetStringType ()


# 23 Notation for the null type -----------------------------------------------

# 23.1
def p_NullType (t):
    'NullType : NULL'
    t[0] = NullType ()

# 23.3
#def p_NullValue (t):
#    'NullValue : NULL'
#    t[0] = t[1]


# 24 Notation for sequence types ----------------------------------------------

# 24.1
def p_SequenceType_1 (t):
    'SequenceType : SEQUENCE LBRACE RBRACE'
    t[0] = SequenceType (elt_list = [])

def p_SequenceType_2 (t):
    'SequenceType : SEQUENCE LBRACE ComponentTypeLists RBRACE'
    if t[3].has_key('ext_list'):
        t[0] = SequenceType (elt_list = t[3]['elt_list'], ext_list = t[3]['ext_list'])
    else:
        t[0] = SequenceType (elt_list = t[3]['elt_list'])

def p_ExtensionAndException_1 (t):
    'ExtensionAndException : ELLIPSIS'
    t[0] = []

def p_OptionalExtensionMarker_1 (t):
    'OptionalExtensionMarker : COMMA ELLIPSIS'
    t[0] = True

def p_OptionalExtensionMarker_2 (t):
    'OptionalExtensionMarker : '
    t[0] = False

def p_ComponentTypeLists_1 (t):
    'ComponentTypeLists : element_type_list'
    t[0] = {'elt_list' : t[1]}

def p_ComponentTypeLists_2 (t):
    'ComponentTypeLists : element_type_list COMMA ExtensionAndException extension_additions OptionalExtensionMarker'
    t[0] = {'elt_list' : t[1], 'ext_list' : t[4]}

def p_ComponentTypeLists_3 (t):
    'ComponentTypeLists : ExtensionAndException extension_additions OptionalExtensionMarker'
    t[0] = {'elt_list' : [], 'ext_list' : t[2]}

def p_extension_additions_1 (t):
    'extension_additions : extension_addition_list'
    t[0] = t[1]

def p_extension_additions_2 (t):
    'extension_additions : '
    t[0] = []

def p_extension_addition_list_1 (t):
    'extension_addition_list : COMMA extension_addition'
    t[0] = [t[2]]

def p_extension_addition_list_2 (t):
    'extension_addition_list : extension_addition_list COMMA extension_addition'
    t[0] = t[1] + [t[3]]

def p_extension_addition_1 (t):
    'extension_addition : element_type'
    t[0] = t[1]

def p_element_type_list_1 (t):
    'element_type_list : element_type'
    t[0] = [t[1]]

def p_element_type_list_2 (t):
    'element_type_list : element_type_list COMMA element_type'
    t[0] = t[1] + [t[3]]

def p_element_type_1 (t):
    'element_type : NamedType'
    t[0] = Node ('elt_type', val = t[1], optional = 0)

def p_element_type_2 (t):
    'element_type : NamedType OPTIONAL'
    t[0] = Node ('elt_type', val = t[1], optional = 1)

def p_element_type_3 (t):
    'element_type : NamedType DEFAULT Value'
    t[0] = Node ('elt_type', val = t[1], optional = 1, default = t[3])
#          /*
#           * this rules uses NamedValue instead of Value
#           * for the stupid choice value syntax (fieldname value)
#           * it should be like a set/seq value (ie with
#           * enclosing { }
#           */

# XXX get to COMPONENTS later

# 24.17
#def p_SequenceValue_1 (t):
#  'SequenceValue : LBRACE RBRACE'
#  t[0] = []


#def p_SequenceValue_2 (t):
#  'SequenceValue : LBRACE ComponentValueList RBRACE'
#  t[0] = t[2]
    
#def p_ComponentValueList_1 (t):
#    'ComponentValueList : NamedValue'
#    t[0] = [t[1]]

#def p_ComponentValueList_2 (t):
#    'ComponentValueList : ComponentValueList COMMA NamedValue'
#    t[0] = t[1] + [t[3]]


# 25 Notation for sequence-of types -------------------------------------------

# 25.1
def p_SequenceOfType (t):
    '''SequenceOfType : SEQUENCE OF Type
                      | SEQUENCE OF NamedType'''
    t[0] = SequenceOfType (val = t[3], size_constr = None)


# 26 Notation for set types ---------------------------------------------------

# 26.1
def p_SetType_1 (t):
    'SetType : SET LBRACE RBRACE'
    if t[3].has_key('ext_list'):
        t[0] = SetType (elt_list = [])

def p_SetType_2 (t):
    'SetType : SET LBRACE ComponentTypeLists RBRACE'
    if t[3].has_key('ext_list'):
        t[0] = SetType (elt_list = t[3]['elt_list'], ext_list = t[3]['ext_list'])
    else:
        t[0] = SetType (elt_list = t[3]['elt_list'])


# 27 Notation for set-of types ------------------------------------------------

# 27.1
def p_SetOfType (t):
    '''SetOfType : SET OF Type
                 | SET OF NamedType'''
    t[0] = SetOfType (val = t[3])

# 28 Notation for choice types ------------------------------------------------

# 28.1
def p_ChoiceType (t):
    'ChoiceType : CHOICE LBRACE alternative_type_lists RBRACE'
    if t[3].has_key('ext_list'):
        t[0] = ChoiceType (elt_list = t[3]['elt_list'], ext_list = t[3]['ext_list'])
    else:
        t[0] = ChoiceType (elt_list = t[3]['elt_list'])

def p_alternative_type_lists_1 (t):
    'alternative_type_lists : alternative_type_list'
    t[0] = {'elt_list' : t[1]}

def p_alternative_type_lists_2 (t):
    '''alternative_type_lists : alternative_type_list COMMA ExtensionAndException extension_addition_alternatives OptionalExtensionMarker'''
    t[0] = {'elt_list' : t[1], 'ext_list' : t[4]}

def p_extension_addition_alternatives_1 (t):
    'extension_addition_alternatives : extension_addition_alternatives_list'
    t[0] = t[1]

def p_extension_addition_alternatives_2 (t):
    'extension_addition_alternatives : '
    t[0] = []

def p_extension_addition_alternatives_list_1 (t):
    'extension_addition_alternatives_list : COMMA extension_addition_alternative'
    t[0] = [t[2]]

def p_extension_addition_alternatives_list_2 (t):
    'extension_addition_alternatives_list : extension_addition_alternatives_list COMMA extension_addition_alternative'
    t[0] = t[1] + [t[3]]

def p_extension_addition_alternative_1 (t):
    'extension_addition_alternative : NamedType'
    t[0] = t[1]

def p_alternative_type_list_1 (t):
    'alternative_type_list : NamedType'
    t[0] = [t[1]]

def p_alternative_type_list_2 (t):
    'alternative_type_list : alternative_type_list COMMA NamedType'
    t[0] = t[1] + [t[3]]

def p_selection_type (t): # XXX what is this?
    'selection_type : identifier LT Type'
    return Node ('seltype', ident = t[1], typ = t[3])

# 30 Notation for tagged types ------------------------------------------------

# 30.1
def p_TaggedType_1 (t):
    'TaggedType : Tag Type'
    t[1].mode = 'default'
    t[0] = t[2]
    t[0].SetTag(t[1])

def p_TaggedType_2 (t):
    '''TaggedType : Tag IMPLICIT Type
                  | Tag EXPLICIT Type'''
    t[1].mode = t[2]
    t[0] = t[3]
    t[0].SetTag(t[1])

def p_Tag (t):
    'Tag : LBRACK Class ClassNumber RBRACK'
    t[0] = Tag(cls = t[2], num = t[3])

def p_ClassNumber_1 (t):
    'ClassNumber : number'
    t[0] = t[1]

def p_ClassNumber_2 (t):
    'ClassNumber : DefinedValue'
    t[0] = t[1]

def p_Class_1 (t):
    '''Class : UNIVERSAL
             | APPLICATION
             | PRIVATE'''
    t[0] = t[1]

def p_Class_2 (t):
    'Class :'
    t[0] = 'CONTEXT'


def p_any_type_1 (t):
    'any_type : ANY'
    t[0] = Literal (val='asn1.ANY')

def p_any_type_2 (t):
    'any_type : ANY DEFINED BY identifier'
    t[0] = Literal (val='asn1.ANY_constr(def_by="%s")' % t[4]) # XXX


# 31 Notation for the object identifier type ----------------------------------

# 31.1
def p_ObjectIdentifierType (t):
  'ObjectIdentifierType : OBJECT IDENTIFIER'
  t[0] = ObjectIdentifierType ()

# 31.3
def p_ObjectIdentifierValue (t):
    'ObjectIdentifierValue : LBRACE oid_comp_list RBRACE'
    t[0] = ObjectIdentifierValue (comp_list=t[2])

def p_oid_comp_list_1 (t):
    'oid_comp_list : oid_comp_list oid_component'
    t[0] = t[1] + [t[2]]

def p_oid_comp_list_2 (t):
    'oid_comp_list : oid_component'
    t[0] = [t[1]]

def p_oid_component (t):
    '''oid_component : number_form
    | name_form
    | name_and_number_form'''
    t[0] = t[1]

def p_number_form (t):
    'number_form : NUMBER'
    t [0] = t[1]

# 36 Notation for character string types --------------------------------------

# 36.1
def p_CharacterStringType (t):
    '''CharacterStringType : RestrictedCharacterStringType
    | UnrestrictedCharacterStringType'''
    t[0] = t[1]


# 37 Definition of restricted character string types --------------------------

def p_RestrictedCharacterStringType_1 (t):
    'RestrictedCharacterStringType : BMPString'
    t[0] = BMPStringType ()
def p_RestrictedCharacterStringType_2 (t):
    'RestrictedCharacterStringType : GeneralString'
    t[0] = GeneralStringType ()
def p_RestrictedCharacterStringType_3 (t):
    'RestrictedCharacterStringType : GraphicString'
    t[0] = GraphicStringType ()
def p_RestrictedCharacterStringType_4 (t):
    'RestrictedCharacterStringType : IA5String'
    t[0] = IA5StringType ()
def p_RestrictedCharacterStringType_5 (t):
    'RestrictedCharacterStringType : ISO646String'
    t[0] = ISO646StringType ()
def p_RestrictedCharacterStringType_6 (t):
    'RestrictedCharacterStringType : NumericString'
    t[0] = NumericStringType ()
def p_RestrictedCharacterStringType_7 (t):
    'RestrictedCharacterStringType : PrintableString'
    t[0] = PrintableStringType ()
def p_RestrictedCharacterStringType_8 (t):
    'RestrictedCharacterStringType : TeletexString'
    t[0] = TeletexStringType ()
def p_RestrictedCharacterStringType_9 (t):
    'RestrictedCharacterStringType : T61String'
    t[0] = T61StringType ()
def p_RestrictedCharacterStringType_10 (t):
    'RestrictedCharacterStringType : UniversalString'
    t[0] = UniversalStringType ()
def p_RestrictedCharacterStringType_11 (t):
    'RestrictedCharacterStringType : UTF8String'
    t[0] = UTF8StringType ()
def p_RestrictedCharacterStringType_12 (t):
    'RestrictedCharacterStringType : VideotexString'
    t[0] = VideotexStringType ()
def p_RestrictedCharacterStringType_13 (t):
    'RestrictedCharacterStringType : VisibleString'
    t[0] = VisibleStringType ()


# 40 Definition of unrestricted character string types ------------------------

# 40.1
def p_UnrestrictedCharacterStringType (t):
    'UnrestrictedCharacterStringType : CHARACTER STRING'
    t[0] = UnrestrictedCharacterStringType ()


# 41 Notation for types defined in clauses 42 to 44 ---------------------------

# 42 Generalized time ---------------------------------------------------------

def p_UsefulType_1 (t):
  'UsefulType : GeneralizedTime'
  t[0] = GeneralizedTime()

# 43 Universal time -----------------------------------------------------------

def p_UsefulType_2 (t):
  'UsefulType : UTCTime'
  t[0] = UTCTime()

# 44 The object descriptor type -----------------------------------------------

def p_UsefulType_3 (t):
  'UsefulType : ObjectDescriptor'
  t[0] = ObjectDescriptor()


# 45 Constrained types --------------------------------------------------------

# 45.1
def p_ConstrainedType_1 (t):
    'ConstrainedType : Type Constraint'
    t[0] = t[1]
    t[0].AddConstraint(t[2])

def p_ConstrainedType_2 (t):
    'ConstrainedType : TypeWithConstraint'
    t[0] = t[1]

# 45.5
def p_TypeWithConstraint_1 (t):
    '''TypeWithConstraint : SET Constraint OF Type
                          | SET SizeConstraint OF Type'''
    t[0] = SetOfType (val = t[4], constr = t[2])

def p_TypeWithConstraint_2 (t):
    '''TypeWithConstraint : SEQUENCE Constraint OF Type
                          | SEQUENCE SizeConstraint OF Type'''
    t[0] = SequenceOfType (val = t[4], constr = t[2])

def p_TypeWithConstraint_3 (t):
    '''TypeWithConstraint : SET Constraint OF NamedType
                          | SET SizeConstraint OF NamedType'''
    t[0] = SetOfType (val = t[4], constr = t[2])

def p_TypeWithConstraint_4 (t):
    '''TypeWithConstraint : SEQUENCE Constraint OF NamedType
                          | SEQUENCE SizeConstraint OF NamedType'''
    t[0] = SequenceOfType (val = t[4], constr = t[2])

# 45.6
# 45.7
def p_Constraint (t):
    'Constraint : LPAREN ConstraintSpec ExceptionSpec RPAREN'
    t[0] = t[2]

def p_ConstraintSpec (t):
    '''ConstraintSpec : ElementSetSpecs
                      | GeneralConstraint'''
    t[0] = t[1]

# 46 Element set specification ------------------------------------------------

# 46.1
def p_ElementSetSpecs_1 (t):
    'ElementSetSpecs : RootElementSetSpec'
    t[0] = t[1]

def p_ElementSetSpecs_2 (t):
    'ElementSetSpecs : RootElementSetSpec COMMA ELLIPSIS'
    t[0] = t[1]
    t[0].ext = True

# skip compound constraints, only simple ones are supported

def p_RootElementSetSpec_1 (t):
    'RootElementSetSpec : SubtypeElements'
    t[0] = t[1]


# 47 Subtype elements ---------------------------------------------------------

# 47.1 General
def p_SubtypeElements (t):
    '''SubtypeElements : SingleValue
                       | ContainedSubtype
                       | ValueRange
                       | PermittedAlphabet
                       | SizeConstraint
                       | InnerTypeConstraints
                       | PatternConstraint'''
    t[0] = t[1]

# 47.2 Single value
# 47.2.1
def p_SingleValue (t):
    'SingleValue : Value'
    t[0] = Constraint(type = 'SingleValue', subtype = t[1]) 

# 47.3 Contained subtype
# 47.3.1
def p_ContainedSubtype (t):
    'ContainedSubtype : Includes Type'
    t[0] = Constraint(type = 'ContainedSubtype', subtype = t[2]) 

def p_Includes (t):
    '''Includes : INCLUDES 
                | '''

# 47.4 Value range
# 47.4.1
def p_ValueRange (t):
    'ValueRange : lower_end_point RANGE upper_end_point'
    t[0] = Constraint(type = 'ValueRange', subtype = [t[1], t[3]])

# 47.4.3
def p_lower_end_point_1 (t):
    'lower_end_point : lower_end_value '
    t[0] = t[1]

def p_lower_end_point_2 (t):
    'lower_end_point : lower_end_value LT' # XXX LT first?
    t[0] = t[1] # but not inclusive range
    
def p_upper_end_point_1 (t):
    'upper_end_point : upper_end_value'
    t[0] = t[1]

def p_upper_end_point_2 (t):
    'upper_end_point : LT upper_end_value'
    t[0] = t[1] # but not inclusive range

def p_lower_end_value (t):
    '''lower_end_value : Value
                       | MIN'''
    t[0] = t[1] # XXX

def p_upper_end_value (t):
    '''upper_end_value : Value
                       | MAX'''
    t[0] = t[1]

# 47.5 Size constraint
# 47.5.1
def p_SizeConstraint (t):
    'SizeConstraint : SIZE Constraint'
    t[0] = Constraint (type = 'Size', subtype = t[2])

# 47.6 Type constraint
# 47.6.1
#def p_TypeConstraint (t):
#    'TypeConstraint : Type'
#    t[0] = Constraint (type = 'Type', subtype = t[2])

# 47.7 Permitted alphabet
# 47.7.1
def p_PermittedAlphabet (t):
    'PermittedAlphabet : FROM Constraint'
    t[0] = Constraint (type = 'From', subtype = t[2])

# 47.8 Inner subtyping
# 47.8.1
def p_InnerTypeConstraints (t):
    '''InnerTypeConstraints : WITH COMPONENT SingleTypeConstraint
                            | WITH COMPONENTS MultipleTypeConstraints'''
    pass # ignore PER invisible constraint

# 47.8.3
def p_SingleTypeConstraint (t):
    'SingleTypeConstraint : Constraint'
    t[0] = t[1]

# 47.8.4
def p_MultipleTypeConstraints (t):
    '''MultipleTypeConstraints : FullSpecification
                               | PartialSpecification'''
    t[0] = t[1]

def p_FullSpecification (t):
    'FullSpecification : LBRACE TypeConstraints RBRACE'
    t[0] = t[2]

def p_PartialSpecification (t):
    'PartialSpecification : LBRACE ELLIPSIS COMMA TypeConstraints RBRACE'
    t[0] = t[4]

def p_TypeConstraints_1 (t):
    'TypeConstraints : named_constraint'
    t [0] = [t[1]]

def p_TypeConstraints_2 (t):
    'TypeConstraints : TypeConstraints COMMA named_constraint'
    t[0] = t[1] + [t[3]]

def p_named_constraint_1 (t):
    'named_constraint : identifier constraint'
    return Node ('named_constraint', ident = t[1], constr = t[2])

def p_named_constraint_2 (t):
    'named_constraint : constraint'
    return Node ('named_constraint', constr = t[1])

def p_constraint (t):
    'constraint : value_constraint presence_constraint'
    t[0] = Node ('constraint', value = t[1], presence = t[2])

def p_value_constraint_1 (t):
    'value_constraint : Constraint'
    t[0] = t[1]

def p_value_constraint_2 (t):
    'value_constraint : '
    pass

def p_presence_constraint_1 (t):
    '''presence_constraint : PRESENT
                 | ABSENT
                 | OPTIONAL'''
    t[0] = t[1]
    
def p_presence_constraint_2 (t):
    '''presence_constraint : '''
    pass

# 47.9 Pattern constraint
# 47.9.1
def p_PatternConstraint (t):
    'PatternConstraint : PATTERN Value'
    t[0] = Constraint (type = 'Pattern', subtype = t[2])

# 49 The exception identifier

# 49.4
def p_ExceptionSpec (t):
    'ExceptionSpec : '
    pass

#  /*-----------------------------------------------------------------------*/
#  /* Value Notation Productions */
#  /*-----------------------------------------------------------------------*/




def p_ext_val_ref (t):
    'ext_val_ref : type_ref DOT identifier'
    # XXX coerce type_ref to module_ref
    return Node ('ext_val_ref', module = t[1], ident = t[3])

def p_special_real_val (t):
    '''special_real_val : PLUS_INFINITY
    | MINUS_INFINITY'''
    t[0] = t[1]


# Note that Z39.50 v3 spec has upper-case here for, e.g., SUTRS.
# I've hacked the grammar to be liberal about what it accepts.
# XXX should have -strict command-line flag to only accept lowercase
# here, since that's what X.208 says.
def p_name_form (t):
    '''name_form : type_ref
    | identifier'''
    t[0] = t[1]

def p_name_and_number_form_1 (t):
    '''name_and_number_form : identifier LPAREN number_form RPAREN
    | type_ref LPAREN number_form RPAREN'''
    t[0] = Node ('name_and_number', ident = t[1], number = t[3])

def p_name_and_number_form_2 (t):
    'name_and_number_form : identifier LPAREN DefinedValue RPAREN'
    t[0] = Node ('name_and_number', ident = t[1], val = t[3])

# see X.208 if you are dubious about lcase only for identifier 
def p_identifier (t):
    'identifier : LCASE_IDENT'
    t[0] = t[1]


def p_binary_string (t):
    'binary_string : BSTRING'
    t[0] = t[1]

def p_hex_string (t):
    'hex_string : HSTRING'
    t[0] = t[1]

def p_char_string (t):
    'char_string : QSTRING'
    t[0] = t[1]

def p_number (t):
    'number : NUMBER'
    t[0] = t[1]


#--- ITU-T Recommendation X.682 -----------------------------------------------

# 8 General constraint specification ------------------------------------------

# 8.1
def p_GeneralConstraint (t):
    '''GeneralConstraint : UserDefinedConstraint'''
#                         | TableConstraint
#                         | ContentsConstraint''
    t[0] = t[1]

# 9 User-defined constraints --------------------------------------------------

# 9.1
def p_UserDefinedConstraint (t):
    'UserDefinedConstraint : CONSTRAINED BY LBRACE UserDefinedConstraintParameterList RBRACE'
    t[0] = Constraint(type = 'UserDefined', subtype = t[4]) 

def p_UserDefinedConstraintParameterList_1 (t):
  'UserDefinedConstraintParameterList : '
  t[0] = []

def p_UserDefinedConstraintParameterList_2 (t):
  'UserDefinedConstraintParameterList : UserDefinedConstraintParameter'
  t[0] = [t[1]]

def p_UserDefinedConstraintParameterList_3 (t):
  'UserDefinedConstraintParameterList : UserDefinedConstraintParameterList COMMA UserDefinedConstraintParameter'
  t[0] = t[1] + [t[3]]

# 9.3
def p_UserDefinedConstraintParameter (t):
  'UserDefinedConstraintParameter : type_ref'
  t[0] = t[1]


#--- ITU-T Recommendation X.683 -----------------------------------------------

# 8 Parameterized assignments -------------------------------------------------

# 8.1

# 8.2
def p_ParameterizedTypeAssignment (t):
  'ParameterizedTypeAssignment : UCASE_IDENT ParameterList ASSIGNMENT Type'
  t[0] = t[4]
  t[0].SetName(t[1] + 'xxx')

# 8.3
def p_ParameterList (t):
    'ParameterList : LBRACE Parameters RBRACE'
    t[0] = t[2]

def p_Parameters_1 (t):
  'Parameters : Parameter'
  t[0] = [t[1]]

def p_Parameters_2 (t):
  'Parameters : Parameters COMMA Parameter'
  t[0] = t[1] + [t[3]]

def p_Parameter_1 (t):
  'Parameter : Type COLON Reference'
  t[0] = [t[1], t[3]]

def p_Parameter_2 (t):
  'Parameter : Reference'
  t[0] = t[1]


# 9 Referencing parameterized definitions -------------------------------------

# 9.1
def p_ParameterizedReference (t):
  'ParameterizedReference : type_ref LBRACE RBRACE'
  t[0] = t[1]
  t[0].val += 'xxx'

# 9.2
def p_ParameterizedType (t):
  'ParameterizedType : type_ref ActualParameterList'
  t[0] = t[1]
  t[0].val += 'xxx'

# 9.5
def p_ActualParameterList (t):
    'ActualParameterList : LBRACE ActualParameters RBRACE'
    t[0] = t[2]

def p_ActualParameters_1 (t):
  'ActualParameters : ActualParameter'
  t[0] = [t[1]]

def p_ActualParameters_2 (t):
  'ActualParameters : ActualParameters COMMA ActualParameter'
  t[0] = t[1] + [t[3]]

def p_ActualParameter (t):
  '''ActualParameter : Type
                     | Value'''
  t[0] = t[1]


def p_error(t):
    raise ParseError(str(t))

yacc.yacc(method='SLR')

def testlex (s):
    lexer.input (s)
    while 1:
        token = lexer.token ()
        if not token:
            break
        print token


def do_module (ast, defined_dict):
    assert (ast.type == 'Module')
    ctx = Ctx (defined_dict)
    print ast.to_python (ctx)
    print ctx.output_assignments ()
    print ctx.output_pyquotes ()

def eth_do_module (ast, ectx):
    assert (ast.type == 'Module')
    if ectx.dbg('s'): print ast.str_depth(0)
    ast.to_eth(ectx)
    ectx.eth_prepare()
    if ectx.dbg('a'):
      print "\n# Assignments"
      print "\n".join(ectx.assign_ord)
      print "\n# Value assignments"
      print "\n".join(ectx.vassign_ord)
    if ectx.dbg('t'):
      print "\n# Imported Types"
      print "%-40s %-24s %-24s" % ("ASN.1 name", "Module", "Protocol")
      print "-" * 100
      for t in ectx.type_imp:
        print "%-40s %-24s %-24s" % (t, ectx.type[t]['import'], ectx.type[t]['proto'])
      print "\n# Imported Values"
      print "%-40s %-24s %-24s" % ("ASN.1 name", "Module", "Protocol")
      print "-" * 100
      for t in ectx.value_imp:
        print "%-40s %-24s %-24s" % (t, ectx.value[t]['import'], ectx.value[t]['proto'])
      print "\n# Exported Types"
      print "%-31s %s" % ("Ethereal type", "Export Flag")
      print "-" * 100
      for t in ectx.eth_export_ord:
        print "%-31s 0x%02X" % (t, ectx.eth_type[t]['export'])
      print "\n# Exported Values"
      print "%-40s %s" % ("Ethereal name", "Value")
      print "-" * 100
      for v in ectx.eth_vexport_ord:
        print "%-40s %s" % (v, ectx.eth_value[v]['value'])
      print "\n# ASN.1 Types"
      print "%-49s %-24s %-24s" % ("ASN.1 unique name", "'tname'", "Ethereal type")
      print "-" * 100
      for t in ectx.type_ord:
        print "%-49s %-24s %-24s" % (t, ectx.type[t]['tname'], ectx.type[t]['ethname'])
      print "\n# Ethereal Types"
      print "Ethereal type                   References (ASN.1 types)"
      print "-" * 100
      for t in ectx.eth_type_ord:
        print "%-31s %d" % (t, len(ectx.eth_type[t]['ref'])),
        print ', '.join(ectx.eth_type[t]['ref'])
      print "\n# ASN.1 Values"
      print "%-40s %-18s %s" % ("ASN.1 unique name", "Type", "Value")
      print "-" * 100
      for v in ectx.value_ord:
        if isinstance (ectx.value[v]['value'], Value):
          print "%-40s %-18s %s" % (v, ectx.value[v]['type'].eth_tname(), ectx.value[v]['value'].to_str())
        else:
          print "%-40s %-18s %s" % (v, ectx.value[v]['type'].eth_tname(), ectx.value[v]['value'])
      print "\n# Ethereal Values"
      print "%-40s %s" % ("Ethereal name", "Value")
      print "-" * 100
      for v in ectx.eth_value_ord:
        print "%-40s %s" % (v, ectx.eth_value[v]['value'])
      print "\n# ASN.1 Fields"
      print "ASN.1 unique name                        Ethereal name        ASN.1 type"
      print "-" * 100
      for f in ectx.field_ord:
        print "%-40s %-20s %s" % (f, ectx.field[f]['ethname'], ectx.field[f]['type'])
      print "\n# Ethereal Fields"
      print "Ethereal name                  Ethereal type        References (ASN.1 fields)"
      print "-" * 100
      for f in ectx.eth_hf_ord:
        print "%-30s %-20s %s" % (f, ectx.eth_hf[f]['ethtype'], len(ectx.eth_hf[f]['ref'])),
        print ', '.join(ectx.eth_hf[f]['ref'])
      #print '\n'.join(ectx.eth_type_ord1)
      print "\n# Cyclic dependencies"
      for c in ectx.eth_dep_cycle:
        print ' -> '.join(c)
    ectx.dupl_report()
    ectx.eth_output_hf()
    ectx.eth_output_ett()
    ectx.eth_output_types()
    ectx.eth_output_hf_arr()
    ectx.eth_output_ett_arr()
    ectx.eth_output_export()
    if ectx.expcnf:
      ectx.eth_output_expcnf()
    ectx.eth_output_val()
    ectx.eth_output_valexp()
    ectx.conform.unused_report()

import time
def testyacc(s, fn, defined_dict):
    ast = yacc.parse(s, debug=0)
    time_str = time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
    print """#!/usr/bin/env python
# Auto-generated from %s at %s
from PyZ3950 import asn1""" % (fn, time_str)
    for module in ast:
      eth_do_module (module, defined_dict)

import sys
import os.path
import getopt

# Ethereal compiler
def eth_usage():
  print """
competh [-h|?] [-d dbg] [-p proto] [-c conform_file] input_file
  -h|?       : usage
  -d dbg     : debug output, dbg = [l][y][s][a][t]
               l - lex 
               y - yacc
               s - internal ASN.1 structure
               a - list of assignments
               t - tables
  -b         : BER (default is PER)
  -X         : original dissector API (see Note)
  -p proto   : protocol name (default is basenam of <input_file> without extension)
  -o name    : output files name (default is <proto>)
  -c conform_file : conformation file
  -e         : create conformation file for exported types
  -s template : single file output (templete is input file without .c/.h extension)
  input_file : input ASN.1 file

Note: It can create output for an original or a new PER/BER dissectors API,
      but the new PER/BER dissectors API is not implemented now.
"""

def eth_fhdr(fn, comment = None):
  def outln(ln):
    if comment:
      return '# %s\n' % (ln)
    else:
      return '/* %-74s */\n' % (ln)
  out = ''
  out += outln('Do not modify this file.')
  out += outln('It is created automatically by the ASN.1 to Ethereal dissector compiler')
  out += outln(fn)
  out += outln(' '.join(sys.argv))
  out += '\n'
  return out

def make_include(out_nm, in_nm, inc_nms, remove_inc=False):
  fin = file(in_nm, "r")
  fout = file(out_nm, "w")
  fout.write(eth_fhdr(out_nm))
  fout.write('/* Input file: ' + in_nm +' */\n')
  fout.write('/* Include files: ' + ', '.join(inc_nms) + ' */\n')
  fout.write('\n')

  include = re.compile(r'^\s*#\s*include\s+[<"](?P<fname>[^>"]+)[>"]', re.IGNORECASE)

  while (True):
    line = fin.readline()
    if (line == ''): break
    result = include.search(line)
    if (result and 
        (result.group('fname') in inc_nms) and
        os.path.exists(result.group('fname'))):
      fout.write('\n')
      fout.write('/*--- Included file: ' + result.group('fname') + ' ---*/\n')
      fout.write('\n')
      finc = file(result.group('fname'), "r")
      fout.write(finc.read())
      fout.write('\n')
      fout.write('/*--- End of included file: ' + result.group('fname') + ' ---*/\n')
      fout.write('\n')
      finc.close()
      if (remove_inc): os.unlink(result.group('fname'))
    else:
      fout.write(line)

  fout.close()
  fin.close()

def eth_main():
  print "ASN.1 to Ethereal dissector compiler";
  try:
    opts, args = getopt.getopt(sys.argv[1:], "h?bXd:p:o:c:es:");
  except getopt.GetoptError:
    eth_usage(); sys.exit(2)
  if len(args) != 1:
    eth_usage(); sys.exit(2)

  fn = args[0];
  conform = EthCnf()
  ectx = EthCtx(conform)
  ectx.encoding = 'per'
  ectx.proto = os.path.splitext(os.path.basename(fn))[0].lower()
  ectx.outnm = ectx.proto
  ectx.new = True
  ectx.dbgopt = ''
  ectx.new = True
  ectx.expcnf = False
  single_file = None
  for o, a in opts:
    if o in ("-h", "-?"):
      eth_usage(); sys.exit(2)
    if o in ("-b",):
      ectx.encoding = 'ber'
    if o in ("-p",):
      ectx.proto = a
      ectx.outnm = ectx.proto
    if o in ("-o",):
      ectx.outnm = a
    if o in ("-c",):
      ectx.conform.read(a)
    if o in ("-X",):
      ectx.new = False
    if o in ("-d",):
      ectx.dbgopt = a
    if o in ("-e",):
      ectx.expcnf = True
    if o in ("-s",):
      single_file = a
  
  f = open(fn, "r")
  s = f.read();
  f.close()
  lexer.debug=ectx.dbg('l')
  ast = yacc.parse(s, debug=ectx.dbg('y'))
  for module in ast:
    eth_do_module(module, ectx)

  if (single_file):
    in_nm = single_file + '.c'
    out_nm = ectx.eth_output_fname('')
    inc_nms = map (lambda x: ectx.eth_output_fname(x), ('hf', 'ett', 'fn', 'hfarr', 'ettarr'))
    inc_nms.extend(map (lambda x: ectx.eth_output_fname(x, ext='h'), ('val',)))
    make_include(out_nm, in_nm, inc_nms, remove_inc=True)
    in_nm = single_file + '.h'
    if (os.path.exists(in_nm)):
      out_nm = ectx.eth_output_fname('', ext='h')
      inc_nms = map (lambda x: ectx.eth_output_fname(x, ext='h'), ('exp', 'valexp'))
      make_include(out_nm, in_nm, inc_nms, remove_inc=True)
    

# Python compiler
def main():
    testfn = testyacc
    if len (sys.argv) == 1:
        while 1:
            s = raw_input ('Query: ')
            if len (s) == 0:
                break
            testfn (s, 'console', {})
    else:
        defined_dict = {}
        for fn in sys.argv [1:]:
            f = open (fn, "r")
            testfn (f.read (), fn, defined_dict)
            f.close ()
            lexer.lineno = 1
  

#--- BODY ---------------------------------------------------------------------

if __name__ == '__main__':
  if ('asn2eth' == os.path.splitext(os.path.basename(sys.argv[0]))[0].lower()):
    eth_main()
  else:
    main()

#------------------------------------------------------------------------------
