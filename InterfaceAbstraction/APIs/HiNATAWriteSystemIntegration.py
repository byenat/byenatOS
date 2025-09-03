"""
ByenatOS HiNATA Write System Integration
HiNATA写入系统集成模块 - 整合所有写入相关组件

这个模块展示了如何将意图识别、写入API、权限管理和对话接口
整合成一个完整的HiNATA写入系统。
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from InterfaceAbstraction.APIs.HiNATAWriteAPI import HiNATAWriteAPI
from InterfaceAbstraction.APIs.ConversationalWriteInterface import ConversationalWriteInterface
from InterfaceAbstraction.APIs.IntentRecognizer import IntentRecognizer
from Security.WritePermissionManager import WritePermissionManager


class HiNATAWriteSystemIntegration:
    """HiNATA写入系统集成类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # 核心组件
        self.write_api = None
        self.conversation_interface = None
        self.permission_manager = None
        self.intent_recognizer = None
        
        # 系统状态
        self.initialized = False
    
    async def initialize(self):
        """初始化整个写入系统"""
        print("正在初始化HiNATA写入系统...")
        
        # 1. 初始化权限管理器
        print("- 初始化权限管理器")
        self.permission_manager = WritePermissionManager(self.config)
        await self.permission_manager.initialize()
        
        # 2. 初始化意图识别器
        print("- 初始化意图识别器")
        self.intent_recognizer = IntentRecognizer()
        
        # 3. 初始化写入API
        print("- 初始化写入API")
        self.write_api = HiNATAWriteAPI(self.config)
        await self.write_api.initialize()
        
        # 4. 初始化对话接口
        print("- 初始化对话接口")
        self.conversation_interface = ConversationalWriteInterface(self.config)
        await self.conversation_interface.initialize()
        
        self.initialized = True
        print("HiNATA写入系统初始化完成!")
    
    async def process_user_request(self, user_id: str, user_input: str, 
                                 context: Dict[str, Any] = None) -> Dict[str, Any]:
        """处理用户请求的完整流程"""
        
        if not self.initialized:
            raise RuntimeError("系统未初始化")
        
        context = context or {}
        start_time = datetime.now(timezone.utc)
        
        try:
            # 1. 意图识别
            print(f"处理用户请求: {user_input}")
            recognized_intent = self.intent_recognizer.recognize_intent(user_input, context)
            
            if recognized_intent.confidence < 0.3:
                return {
                    "status": "intent_not_recognized",
                    "message": "抱歉，我没有理解您的意图。请更具体地描述您想要执行的操作。",
                    "suggestions": [
                        "使用明确的动词，如'添加'、'删除'、'修改'",
                        "指定要操作的内容类型",
                        "提供筛选条件"
                    ]
                }
            
            print(f"识别的意图: {recognized_intent.intent_type.value} (置信度: {recognized_intent.confidence:.2f})")
            
            # 2. 权限验证
            operation_data = {
                "operation_type": recognized_intent.operation_type.value,
                "estimated_affected_count": recognized_intent.parameters.get("estimated_count", 1),
                "target_sources": list(recognized_intent.target_filter.get("sources", []))
            }
            
            permission_context = {
                "source_app": "hinata_write_system",
                "session_id": context.get("session_id", ""),
                "ip_address": context.get("ip_address", ""),
                "user_agent": context.get("user_agent", "")
            }
            
            allowed, reason, audit_id = await self.permission_manager.validate_and_audit_operation(
                user_id, recognized_intent.operation_type.value, operation_data, permission_context
            )
            
            if not allowed:
                return {
                    "status": "permission_denied",
                    "message": f"权限不足: {reason}",
                    "audit_id": audit_id,
                    "required_action": self._get_permission_help(reason)
                }
            
            print(f"权限验证通过 (审计ID: {audit_id})")
            
            # 3. 执行试运行
            dry_run_result = await self._execute_dry_run(user_id, recognized_intent)
            
            if dry_run_result["estimated_affected"] == 0:
                return {
                    "status": "no_matches",
                    "message": "没有找到符合条件的记录",
                    "filters_used": recognized_intent.target_filter,
                    "suggestions": [
                        "检查筛选条件是否正确",
                        "尝试使用更宽泛的搜索条件",
                        "确认相关内容确实存在"
                    ]
                }
            
            # 4. 返回预览结果和确认请求
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            return {
                "status": "preview_ready",
                "intent": {
                    "type": recognized_intent.intent_type.value,
                    "confidence": recognized_intent.confidence,
                    "description": recognized_intent.user_description
                },
                "preview": dry_run_result,
                "confirmation_message": recognized_intent.suggested_confirmation,
                "audit_id": audit_id,
                "processing_time": processing_time,
                "next_steps": [
                    "确认操作无误",
                    "调用执行接口完成操作",
                    "操作前会自动创建备份"
                ]
            }
            
        except Exception as e:
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            return {
                "status": "error",
                "message": f"处理请求时发生错误: {str(e)}",
                "processing_time": processing_time,
                "error_type": type(e).__name__
            }
    
    async def execute_confirmed_operation(self, user_id: str, audit_id: str, 
                                        modifications: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行已确认的操作"""
        
        if not self.initialized:
            raise RuntimeError("系统未初始化")
        
        try:
            # 从审计日志获取操作详情
            audit_logs = await self.permission_manager.get_audit_logs(
                user_id=user_id, limit=1, offset=0
            )
            
            if not audit_logs or audit_logs[0]["log_id"] != audit_id:
                return {
                    "status": "audit_not_found",
                    "message": "未找到对应的审计记录或记录已过期"
                }
            
            audit_log = audit_logs[0]
            
            if not audit_log["permission_check_result"]:
                return {
                    "status": "permission_revoked",
                    "message": "操作权限已被撤销"
                }
            
            # 重新构建操作请求
            operation_details = json.loads(audit_log["operation_details"])
            
            # 这里应该根据audit_log重建完整的写入请求
            # 为了简化，我们返回一个模拟的执行结果
            
            execution_result = {
                "status": "completed",
                "affected_count": operation_details.get("estimated_affected_count", 1),
                "processing_time": 0.5,
                "operation_id": f"exec_{audit_id}",
                "backup_created": True,
                "modifications_applied": modifications or {}
            }
            
            # 更新审计日志
            await self._update_audit_log_execution(audit_id, execution_result)
            
            return {
                "status": "success",
                "message": "操作执行成功",
                "results": execution_result,
                "audit_id": audit_id
            }
            
        except Exception as e:
            return {
                "status": "execution_failed",
                "message": f"执行操作时发生错误: {str(e)}",
                "error_type": type(e).__name__
            }
    
    async def get_user_operation_history(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """获取用户操作历史"""
        
        try:
            audit_logs = await self.permission_manager.get_audit_logs(
                user_id=user_id, limit=limit, offset=0
            )
            
            history = []
            for log in audit_logs:
                history.append({
                    "audit_id": log["log_id"],
                    "operation_type": log["operation_type"],
                    "requested_at": log["requested_at"],
                    "executed": log["executed_at"] is not None,
                    "status": log["execution_result"],
                    "affected_records": log["affected_records"],
                    "risk_level": log["risk_level"]
                })
            
            return {
                "status": "success",
                "user_id": user_id,
                "history": history,
                "total_operations": len(history)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"获取操作历史失败: {str(e)}"
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        
        status = {
            "initialized": self.initialized,
            "components": {
                "write_api": self.write_api is not None,
                "conversation_interface": self.conversation_interface is not None,
                "permission_manager": self.permission_manager is not None,
                "intent_recognizer": self.intent_recognizer is not None
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if self.initialized:
            # 获取一些系统统计信息
            try:
                recent_logs = await self.permission_manager.get_audit_logs(limit=10)
                status["recent_activity"] = {
                    "total_operations_last_10": len(recent_logs),
                    "successful_operations": len([log for log in recent_logs if log["execution_result"] == "completed"]),
                    "failed_operations": len([log for log in recent_logs if log["execution_result"] == "failed"])
                }
            except:
                status["recent_activity"] = {"error": "无法获取活动统计"}
        
        return status
    
    async def _execute_dry_run(self, user_id: str, recognized_intent) -> Dict[str, Any]:
        """执行试运行"""
        
        # 这里应该调用实际的写入API进行试运行
        # 为了简化，我们返回一个模拟结果
        
        estimated_count = recognized_intent.parameters.get("estimated_count", 1)
        
        return {
            "estimated_affected": estimated_count,
            "preview_results": [
                f"示例记录1 - 将被{recognized_intent.operation_type.value}",
                f"示例记录2 - 将被{recognized_intent.operation_type.value}",
                "..."
            ][:min(estimated_count, 5)],
            "warnings": [],
            "dry_run": True
        }
    
    async def _update_audit_log_execution(self, audit_id: str, execution_result: Dict[str, Any]):
        """更新审计日志的执行结果"""
        
        # 这里应该更新数据库中的审计日志
        # 为了简化，我们只是打印日志
        print(f"更新审计日志 {audit_id}: {execution_result}")
    
    def _get_permission_help(self, reason: str) -> str:
        """获取权限帮助信息"""
        
        help_messages = {
            "No write permissions": "请联系管理员申请写入权限",
            "Read-only access": "您当前只有只读权限，需要申请写入权限",
            "Daily operation limit exceeded": "您今日的操作次数已达上限，请明天再试",
            "Batch size limit exceeded": "批次大小超出限制，请减少操作范围或申请更高权限",
            "Admin permissions required": "此操作需要管理员权限",
            "Two-factor authentication required": "请启用两因子认证后重试"
        }
        
        return help_messages.get(reason, "请检查您的权限设置或联系管理员")
    
    async def close(self):
        """关闭系统"""
        print("正在关闭HiNATA写入系统...")
        
        if self.permission_manager:
            await self.permission_manager.close()
        
        if self.write_api:
            # 这里应该有close方法
            pass
        
        print("系统已关闭")


# 使用示例
async def main():
    """使用示例"""
    
    # 系统配置
    config = {
        'postgres_dsn': 'postgresql://user:password@localhost/byenatos',
        'redis_url': 'redis://localhost:6379',
        'cold_storage_path': '/data/cold_storage',
        'chroma_persist_dir': '/data/chroma',
        'elasticsearch_url': 'http://localhost:9200'
    }
    
    # 创建并初始化系统
    write_system = HiNATAWriteSystemIntegration(config)
    await write_system.initialize()
    
    try:
        # 测试用户请求处理
        user_id = "test_user_123"
        user_input = "请为所有关于Python的笔记添加'编程语言'标签"
        
        print("\n=== 处理用户请求 ===")
        result = await write_system.process_user_request(user_id, user_input)
        print(f"处理结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # 如果有审计ID，模拟执行确认的操作
        if result.get("status") == "preview_ready":
            audit_id = result.get("audit_id")
            print(f"\n=== 执行确认的操作 (审计ID: {audit_id}) ===")
            
            execution_result = await write_system.execute_confirmed_operation(user_id, audit_id)
            print(f"执行结果: {json.dumps(execution_result, indent=2, ensure_ascii=False)}")
        
        # 获取操作历史
        print(f"\n=== 获取用户操作历史 ===")
        history = await write_system.get_user_operation_history(user_id)
        print(f"操作历史: {json.dumps(history, indent=2, ensure_ascii=False)}")
        
        # 获取系统状态
        print(f"\n=== 系统状态 ===")
        status = await write_system.get_system_status()
        print(f"系统状态: {json.dumps(status, indent=2, ensure_ascii=False)}")
        
    finally:
        await write_system.close()


if __name__ == "__main__":
    asyncio.run(main())