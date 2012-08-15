# Generated by the protocol buffer compiler.  DO NOT EDIT!

from google.protobuf import descriptor
from google.protobuf import message
from google.protobuf import reflection
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)



DESCRIPTOR = descriptor.FileDescriptor(
  name='rvlib.proto',
  package='',
  serialized_pb='\n\x0brvlib.proto\"\x1e\n\x03Job\x12\n\n\x02id\x18\x01 \x02(\x05\x12\x0b\n\x03url\x18\x02 \x02(\t\"j\n\x0fManagerResponse\x12\'\n\x06status\x18\x01 \x02(\x0e\x32\x17.ManagerResponse.Status\x12\x11\n\x03job\x18\x02 \x01(\x0b\x32\x04.Job\"\x1b\n\x06Status\x12\x07\n\x03JOB\x10\x01\x12\x08\n\x04WAIT\x10\x02\"E\n\rWorkerRequest\x12!\n\x04type\x18\x01 \x02(\x0e\x32\x13.WorkerRequest.Type\"\x11\n\x04Type\x12\t\n\x05READY\x10\x01\"\x81\x01\n\x08JobEvent\x12\x0e\n\x06job_id\x18\x01 \x02(\x05\x12\x1c\n\x04type\x18\x02 \x02(\x0e\x32\x0e.JobEvent.Type\x12\r\n\x05\x65rror\x18\x03 \x01(\t\x12\x0c\n\x04meta\x18\x04 \x01(\t\"*\n\x04Type\x12\r\n\tHEARTBEAT\x10\x01\x12\t\n\x05\x45RROR\x10\x02\x12\x08\n\x04META\x10\x03\"\\\n\x10JobEventResponse\x12(\n\x06status\x18\x01 \x02(\x0e\x32\x18.JobEventResponse.Status\"\x1e\n\x06Status\x12\x06\n\x02OK\x10\x01\x12\x0c\n\x08JOB_GONE\x10\x02\"S\n\x05Track\x12\n\n\x02id\x18\x01 \x02(\x05\x12\r\n\x05title\x18\x02 \x02(\t\x12\x0e\n\x06\x61rtist\x18\x03 \x01(\t\x12\x0c\n\x04name\x18\x04 \x01(\t\x12\x11\n\timage_url\x18\x05 \x01(\t\"K\n\x0bOnairUpdate\x12\x12\n\nstation_id\x18\x01 \x02(\x05\x12\x11\n\tstream_id\x18\x02 \x02(\x05\x12\x15\n\x05track\x18\x03 \x02(\x0b\x32\x06.Track\"\x94\x01\n\x0cStreamStatus\x12 \n\x04type\x18\x01 \x02(\x0e\x32\x12.StreamStatus.Type\x12\x12\n\nstation_id\x18\x02 \x02(\x05\x12\x11\n\tstream_id\x18\x03 \x02(\x05\x12\x0f\n\x07\x63lients\x18\x04 \x02(\x05\"*\n\x04Type\x12\n\n\x06ONLINE\x10\x01\x12\x0b\n\x07OFFLINE\x10\x02\x12\t\n\x05TOUCH\x10\x03')



_MANAGERRESPONSE_STATUS = descriptor.EnumDescriptor(
  name='Status',
  full_name='ManagerResponse.Status',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='JOB', index=0, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='WAIT', index=1, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=126,
  serialized_end=153,
)

_WORKERREQUEST_TYPE = descriptor.EnumDescriptor(
  name='Type',
  full_name='WorkerRequest.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='READY', index=0, number=1,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=207,
  serialized_end=224,
)

_JOBEVENT_TYPE = descriptor.EnumDescriptor(
  name='Type',
  full_name='JobEvent.Type',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='HEARTBEAT', index=0, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='ERROR', index=1, number=2,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='META', index=2, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=314,
  serialized_end=356,
)

_JOBEVENTRESPONSE_STATUS = descriptor.EnumDescriptor(
  name='Status',
  full_name='JobEventResponse.Status',
  filename=None,
  file=DESCRIPTOR,
  values=[
    descriptor.EnumValueDescriptor(
      name='OK', index=0, number=1,
      options=None,
      type=None),
    descriptor.EnumValueDescriptor(
      name='JOB_GONE', index=1, number=2,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=420,
  serialized_end=450,
)

_STREAMSTATUS_TYPE = descriptor.EnumDescriptor(
  name='Type',
  full_name='StreamStatus.Type',
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
    descriptor.EnumValueDescriptor(
      name='TOUCH', index=2, number=3,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=None,
  serialized_start=721,
  serialized_end=763,
)


_JOB = descriptor.Descriptor(
  name='Job',
  full_name='Job',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='id', full_name='Job.id', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='url', full_name='Job.url', index=1,
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
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=15,
  serialized_end=45,
)


_MANAGERRESPONSE = descriptor.Descriptor(
  name='ManagerResponse',
  full_name='ManagerResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='status', full_name='ManagerResponse.status', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='job', full_name='ManagerResponse.job', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _MANAGERRESPONSE_STATUS,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=47,
  serialized_end=153,
)


_WORKERREQUEST = descriptor.Descriptor(
  name='WorkerRequest',
  full_name='WorkerRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='type', full_name='WorkerRequest.type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _WORKERREQUEST_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=155,
  serialized_end=224,
)


_JOBEVENT = descriptor.Descriptor(
  name='JobEvent',
  full_name='JobEvent',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='job_id', full_name='JobEvent.job_id', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='type', full_name='JobEvent.type', index=1,
      number=2, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='error', full_name='JobEvent.error', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='meta', full_name='JobEvent.meta', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _JOBEVENT_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=227,
  serialized_end=356,
)


_JOBEVENTRESPONSE = descriptor.Descriptor(
  name='JobEventResponse',
  full_name='JobEventResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='status', full_name='JobEventResponse.status', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _JOBEVENTRESPONSE_STATUS,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=358,
  serialized_end=450,
)


_TRACK = descriptor.Descriptor(
  name='Track',
  full_name='Track',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='id', full_name='Track.id', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='title', full_name='Track.title', index=1,
      number=2, type=9, cpp_type=9, label=2,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='artist', full_name='Track.artist', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='name', full_name='Track.name', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=unicode("", "utf-8"),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='image_url', full_name='Track.image_url', index=4,
      number=5, type=9, cpp_type=9, label=1,
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
  serialized_start=452,
  serialized_end=535,
)


_ONAIRUPDATE = descriptor.Descriptor(
  name='OnairUpdate',
  full_name='OnairUpdate',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='station_id', full_name='OnairUpdate.station_id', index=0,
      number=1, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='stream_id', full_name='OnairUpdate.stream_id', index=1,
      number=2, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='track', full_name='OnairUpdate.track', index=2,
      number=3, type=11, cpp_type=10, label=2,
      has_default_value=False, default_value=None,
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
  serialized_start=537,
  serialized_end=612,
)


_STREAMSTATUS = descriptor.Descriptor(
  name='StreamStatus',
  full_name='StreamStatus',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    descriptor.FieldDescriptor(
      name='type', full_name='StreamStatus.type', index=0,
      number=1, type=14, cpp_type=8, label=2,
      has_default_value=False, default_value=1,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='station_id', full_name='StreamStatus.station_id', index=1,
      number=2, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='stream_id', full_name='StreamStatus.stream_id', index=2,
      number=3, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
    descriptor.FieldDescriptor(
      name='clients', full_name='StreamStatus.clients', index=3,
      number=4, type=5, cpp_type=1, label=2,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
    _STREAMSTATUS_TYPE,
  ],
  options=None,
  is_extendable=False,
  extension_ranges=[],
  serialized_start=615,
  serialized_end=763,
)

_MANAGERRESPONSE.fields_by_name['status'].enum_type = _MANAGERRESPONSE_STATUS
_MANAGERRESPONSE.fields_by_name['job'].message_type = _JOB
_MANAGERRESPONSE_STATUS.containing_type = _MANAGERRESPONSE;
_WORKERREQUEST.fields_by_name['type'].enum_type = _WORKERREQUEST_TYPE
_WORKERREQUEST_TYPE.containing_type = _WORKERREQUEST;
_JOBEVENT.fields_by_name['type'].enum_type = _JOBEVENT_TYPE
_JOBEVENT_TYPE.containing_type = _JOBEVENT;
_JOBEVENTRESPONSE.fields_by_name['status'].enum_type = _JOBEVENTRESPONSE_STATUS
_JOBEVENTRESPONSE_STATUS.containing_type = _JOBEVENTRESPONSE;
_ONAIRUPDATE.fields_by_name['track'].message_type = _TRACK
_STREAMSTATUS.fields_by_name['type'].enum_type = _STREAMSTATUS_TYPE
_STREAMSTATUS_TYPE.containing_type = _STREAMSTATUS;
DESCRIPTOR.message_types_by_name['Job'] = _JOB
DESCRIPTOR.message_types_by_name['ManagerResponse'] = _MANAGERRESPONSE
DESCRIPTOR.message_types_by_name['WorkerRequest'] = _WORKERREQUEST
DESCRIPTOR.message_types_by_name['JobEvent'] = _JOBEVENT
DESCRIPTOR.message_types_by_name['JobEventResponse'] = _JOBEVENTRESPONSE
DESCRIPTOR.message_types_by_name['Track'] = _TRACK
DESCRIPTOR.message_types_by_name['OnairUpdate'] = _ONAIRUPDATE
DESCRIPTOR.message_types_by_name['StreamStatus'] = _STREAMSTATUS

class Job(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _JOB
  
  # @@protoc_insertion_point(class_scope:Job)

class ManagerResponse(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _MANAGERRESPONSE
  
  # @@protoc_insertion_point(class_scope:ManagerResponse)

class WorkerRequest(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _WORKERREQUEST
  
  # @@protoc_insertion_point(class_scope:WorkerRequest)

class JobEvent(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _JOBEVENT
  
  # @@protoc_insertion_point(class_scope:JobEvent)

class JobEventResponse(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _JOBEVENTRESPONSE
  
  # @@protoc_insertion_point(class_scope:JobEventResponse)

class Track(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _TRACK
  
  # @@protoc_insertion_point(class_scope:Track)

class OnairUpdate(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _ONAIRUPDATE
  
  # @@protoc_insertion_point(class_scope:OnairUpdate)

class StreamStatus(message.Message):
  __metaclass__ = reflection.GeneratedProtocolMessageType
  DESCRIPTOR = _STREAMSTATUS
  
  # @@protoc_insertion_point(class_scope:StreamStatus)

# @@protoc_insertion_point(module_scope)
