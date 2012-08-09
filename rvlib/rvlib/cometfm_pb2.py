# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='cometfm.proto',
  package='',
  serialized_pb='\n\rcometfm.proto\" \n\rRequestUpdate\x12\x0f\n\x07\x63hannel\x18\x01 \x02(\t\"h\n\x0cStreamStatus\x12$\n\x06status\x18\x01 \x02(\x0e\x32\x14.StreamStatus.Status\x12\x0f\n\x07\x63hannel\x18\x02 \x02(\t\"!\n\x06Status\x12\n\n\x06ONLINE\x10\x01\x12\x0b\n\x07OFFLINE\x10\x02')



_STREAMSTATUS_STATUS = descriptor.EnumDescriptor(
  name='Status',
  full_name='StreamStatus.Status',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='ONLINE', index=0, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='OFFLINE', index=1, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=122,
  serialized_end=155,
)


_REQUESTUPDATE = descriptor.Descriptor(
  name='RequestUpdate',
  full_name='RequestUpdate',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='channel', full_name='RequestUpdate.channel', index=0,
      number=1, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=17,
  serialized_end=49,
)


_STREAMSTATUS = descriptor.Descriptor(
  name='StreamStatus',
  full_name='StreamStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='status', full_name='StreamStatus.status', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='channel', full_name='StreamStatus.channel', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _STREAMSTATUS_STATUS,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=51,
  serialized_end=155,
)

_STREAMSTATUS.fields_by_name['status'].enum_type = _STREAMSTATUS_STATUS
_STREAMSTATUS_STATUS.containing_type = _STREAMSTATUS;
DESCRIPTOR.message_types_by_name['RequestUpdate'] = _REQUESTUPDATE
DESCRIPTOR.message_types_by_name['StreamStatus'] = _STREAMSTATUS

class RequestUpdate(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _REQUESTUPDATE
  
  # @@protoc_insertion_point(class_scope:RequestUpdate)

class StreamStatus(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _STREAMSTATUS
  
  # @@protoc_insertion_point(class_scope:StreamStatus)

# @@protoc_insertion_point(module_scope)
