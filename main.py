# 导入日志监控库logfire
import logfire

# 配置logfire日志监控
logfire.configure()
# 对pydantic_ai进行监控
logfire.instrument_pydantic_ai()
