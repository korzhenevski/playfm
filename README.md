tracefm
=======

TODO:

обработка ошибок платформы
для редиса делаем две попытки и кидаем исключение
для монги две попытки реконнекта
для зеромкью таймаут на send/receive 1 секунда

воркеры шлют телеметрию на менеджер.
- пид, память
- загрузка cpu процессом и общая
- аптайм
- утилизация канала: трафик от задач
- кол-во задач и трекинг последних эвентов (event_type_at)

message WorkerTelemetry {
  required int32 pid = 1;
  required float cpu = 2;
  required float process_cpu;
  required int64 memory_usage;
  required int64 process_memory_usage;
  required int32 memory_usage;
  required int32 uptime;
  optional int32 traffic_in;
  message Job {
    required int32 job_id;
  }
  repeated Job jobs;
}
              
менеджер хранит состояние в файле.
снепшот уходит раз в 5 сек при налиции изменений

message ManagerStream {
  required int32 id = 1;
  required int32 station_id = 2;
  enum State {
    PERSISTENT = 1;
    ONDEMAND = 2;
  }
  required State state = 3 [default=ONDEMAND];
  optional int32 record_id;
  
  record_id выставляется из-вне
  запросом recordStream(stream_id, station_id, record_id)
}

таким образом, после рестарта, менеджер всегда знает что ему делать с потоками


RadioVoice Platform ™