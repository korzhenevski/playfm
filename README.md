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
              

RadioVoice Platform ™