"""
ByenatOS Conversational Write Interface
对话式写入接口 - 整合意图识别和HiNATA写入操作

当用户通过对话框表达修改知识库内容的意图时，
此接口负责理解用户意图并执行相应的HiNATA写入操作。
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from InterfaceAbstraction.APIs.IntentRecognizer import IntentRecognizer, RecognizedIntent, IntentType
from InterfaceAbstraction.APIs.HiNATAWriteAPI import (
    HiNATAWriteAPI, HiNATAWriteRequestModel, HiNATAWriteModel, 
    BulkOperationModel, WriteOperationContext
)
from InterfaceAbstraction.APIs.AppIntegrationAPI import AuthManager


# 请求模型
class ConversationalWriteRequest(BaseModel):
    """对话式写入请求"""
    user_id: str = Field(..., description="用户ID")
    user_input: str = Field(..., description="用户的自然语言输入")
    context: Dict[str, Any] = Field(default={}, description="对话上下文")
    auto_confirm: bool = Field(default=False, description="是否自动确认执行")
    dry_run: bool = Field(default=True, description="是否为试运行")


class IntentConfirmationRequest(BaseModel):
    """意图确认请求"""
    session_id: str = Field(..., description="会话ID")
    user_id: str = Field(..., description="用户ID")
    confirmed: bool = Field(..., description="用户是否确认")
    modifications: Dict[str, Any] = Field(default={}, description="用户对操作的修改")


# 响应模型
class ConversationalWriteResponse(BaseModel):
    """对话式写入响应"""
    session_id: str
    status: str
    intent_recognized: bool
    intent_confidence: float
    suggested_action: str
    confirmation_required: bool
    preview_results: Optional[Dict[str, Any]] = None
    execution_results: Optional[Dict[str, Any]] = None
    next_steps: List[str] = Field(default=[])
    error_message: Optional[str] = None


@dataclass
class WriteSession:
    """写入会话"""
    session_id: str
    user_id: str
    recognized_intent: RecognizedIntent
    write_request: HiNATAWriteRequestModel
    created_at: str
    confirmed: bool = False
    executed: bool = False
    results: Optional[Dict[str, Any]] = None


class ConversationalWriteInterface:
    """对话式写入接口"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.app = FastAPI(
            title="ByenatOS Conversational Write Interface",
            description="ByenatOS对话式HiNATA写入接口",
            version="1.0.0"
        )
        
        # 初始化组件
        self.intent_recognizer = IntentRecognizer()
        self.write_api = None
        self.auth_manager = None
        
        # 会话存储（生产环境应使用Redis）
        self.active_sessions: Dict[str, WriteSession] = {}
        
        # 设置路由
        self._setup_routes()
    
    async def initialize(self):
        """初始化接口"""
        # 初始化写入API
        self.write_api = HiNATAWriteAPI(self.config)
        await self.write_api.initialize()
        
        # 获取认证管理器
        self.auth_manager = self.write_api.auth_manager
    
    def _setup_routes(self):
        """设置API路由"""
        security = HTTPBearer()
        
        async def get_current_app(credentials: HTTPAuthorizationCredentials = Security(security)):
            """获取当前认证的App"""
            app = await self.auth_manager.authenticate_app(credentials.credentials)
            if not app:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid API key"
                )
            return app
        
        # 1. 对话式写入请求处理
        @self.app.post("/api/conversation/write", response_model=ConversationalWriteResponse)
        async def process_conversational_write(
            request: ConversationalWriteRequest,
            app = Depends(get_current_app)
        ):
            """处理对话式写入请求"""
            
            try:
                # 1. 意图识别
                recognized_intent = self.intent_recognizer.recognize_intent(
                    request.user_input, 
                    request.context
                )
                
                session_id = f"session_{int(time.time())}_{request.user_id}"
                
                # 2. 检查意图是否有效
                if recognized_intent.intent_type == IntentType.NONE or recognized_intent.confidence < 0.3:
                    return ConversationalWriteResponse(
                        session_id=session_id,
                        status="no_intent",
                        intent_recognized=False,
                        intent_confidence=recognized_intent.confidence,
                        suggested_action="我没有理解您想要执行的操作。请更具体地描述您希望对知识库进行的修改。",
                        confirmation_required=False,
                        next_steps=["请重新描述您的需求", "使用更具体的动词，如'添加'、'删除'、'修改'等"]
                    )
                
                # 3. 构建写入请求
                write_request = await self._build_write_request(recognized_intent, request)
                
                # 4. 创建会话
                session = WriteSession(
                    session_id=session_id,
                    user_id=request.user_id,
                    recognized_intent=recognized_intent,
                    write_request=write_request,
                    created_at=datetime.now(timezone.utc).isoformat()
                )
                self.active_sessions[session_id] = session
                
                # 5. 执行试运行（如果需要）
                preview_results = None
                if request.dry_run:
                    preview_results = await self._execute_dry_run(write_request, session_id)
                
                # 6. 自动执行（如果用户确认）
                execution_results = None
                if request.auto_confirm and not request.dry_run:
                    execution_results = await self._execute_write_operation(write_request, session)
                    session.executed = True
                    session.confirmed = True
                    session.results = execution_results
                
                # 7. 生成响应
                return ConversationalWriteResponse(
                    session_id=session_id,
                    status="success",
                    intent_recognized=True,
                    intent_confidence=recognized_intent.confidence,
                    suggested_action=recognized_intent.suggested_confirmation,
                    confirmation_required=not request.auto_confirm,
                    preview_results=preview_results,
                    execution_results=execution_results,
                    next_steps=self._generate_next_steps(recognized_intent, preview_results)
                )
                
            except Exception as e:
                return ConversationalWriteResponse(
                    session_id=f"error_{int(time.time())}",
                    status="error",
                    intent_recognized=False,
                    intent_confidence=0.0,
                    suggested_action="处理请求时发生错误",
                    confirmation_required=False,
                    error_message=str(e)
                )
        
        # 2. 意图确认和执行
        @self.app.post("/api/conversation/confirm", response_model=ConversationalWriteResponse)
        async def confirm_and_execute(
            request: IntentConfirmationRequest,
            app = Depends(get_current_app)
        ):
            """确认意图并执行操作"""
            
            session = self.active_sessions.get(request.session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found or expired"
                )
            
            if session.user_id != request.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Session belongs to different user"
                )
            
            if not request.confirmed:
                # 用户取消操作
                del self.active_sessions[request.session_id]
                return ConversationalWriteResponse(
                    session_id=request.session_id,
                    status="cancelled",
                    intent_recognized=True,
                    intent_confidence=session.recognized_intent.confidence,
                    suggested_action="操作已取消",
                    confirmation_required=False,
                    next_steps=["如需其他操作，请重新发起请求"]
                )
            
            try:
                # 应用用户修改
                if request.modifications:
                    session.write_request = self._apply_user_modifications(
                        session.write_request, 
                        request.modifications
                    )
                
                # 执行操作
                execution_results = await self._execute_write_operation(
                    session.write_request, 
                    session
                )
                
                session.executed = True
                session.confirmed = True
                session.results = execution_results
                
                return ConversationalWriteResponse(
                    session_id=request.session_id,
                    status="executed",
                    intent_recognized=True,
                    intent_confidence=session.recognized_intent.confidence,
                    suggested_action="操作已成功执行",
                    confirmation_required=False,
                    execution_results=execution_results,
                    next_steps=["操作完成", "您可以查看修改结果"]
                )
                
            except Exception as e:
                return ConversationalWriteResponse(
                    session_id=request.session_id,
                    status="execution_failed",
                    intent_recognized=True,
                    intent_confidence=session.recognized_intent.confidence,
                    suggested_action="执行操作时发生错误",
                    confirmation_required=False,
                    error_message=str(e),
                    next_steps=["请检查错误信息", "可能需要修改操作参数"]
                )
        
        # 3. 会话状态查询
        @self.app.get("/api/conversation/session/{session_id}")
        async def get_session_status(
            session_id: str,
            app = Depends(get_current_app)
        ):
            """获取会话状态"""
            
            session = self.active_sessions.get(session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            
            return {
                "session_id": session.session_id,
                "user_id": session.user_id,
                "intent_type": session.recognized_intent.intent_type.value,
                "confidence": session.recognized_intent.confidence,
                "confirmed": session.confirmed,
                "executed": session.executed,
                "created_at": session.created_at,
                "results_available": session.results is not None
            }
        
        # 4. 意图重新识别
        @self.app.post("/api/conversation/reinterpret")
        async def reinterpret_intent(
            session_id: str,
            new_input: str,
            app = Depends(get_current_app)
        ):
            """重新解释用户意图"""
            
            session = self.active_sessions.get(session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Session not found"
                )
            
            # 重新识别意图
            new_intent = self.intent_recognizer.recognize_intent(new_input)
            
            # 更新会话
            session.recognized_intent = new_intent
            session.write_request = await self._build_write_request(
                new_intent, 
                ConversationalWriteRequest(
                    user_id=session.user_id,
                    user_input=new_input,
                    dry_run=True
                )
            )
            
            return {
                "session_id": session_id,
                "new_intent": new_intent.intent_type.value,
                "confidence": new_intent.confidence,
                "suggested_action": new_intent.suggested_confirmation
            }
    
    async def _build_write_request(self, intent: RecognizedIntent, 
                                 request: ConversationalWriteRequest) -> HiNATAWriteRequestModel:
        """构建写入请求"""
        
        # 基础请求数据
        write_request_data = {
            "user_id": request.user_id,
            "operation_type": intent.operation_type.value,
            "intent_description": intent.user_description,
            "processing_options": {
                "dry_run": request.dry_run,
                "auto_backup": True,
                "validation_strict": True
            }
        }
        
        # 根据意图类型构建具体数据
        if intent.operation_type.value in ["bulk_tag", "bulk_retag", "batch_update"]:
            write_request_data["bulk_operation"] = BulkOperationModel(
                operation_type=intent.operation_type.value,
                target_filter=intent.target_filter,
                operation_data=intent.operation_data,
                dry_run=request.dry_run,
                batch_size=100
            )
        
        elif intent.operation_type.value == "create":
            # 构建创建请求
            hinata_data = HiNATAWriteModel(
                source="conversational_interface",
                highlight=intent.operation_data.get("highlight", ""),
                note=intent.operation_data.get("note", ""),
                address=intent.operation_data.get("address", "conversation://user_intent"),
                tag=intent.operation_data.get("tag", []),
                access=intent.operation_data.get("access", "private")
            )
            write_request_data["hinata_data"] = hinata_data
        
        elif intent.operation_type.value == "delete":
            # 删除操作的特殊处理
            write_request_data["processing_options"]["hinata_ids"] = intent.parameters.get("hinata_ids", [])
            write_request_data["processing_options"]["soft_delete"] = True
        
        return HiNATAWriteRequestModel(**write_request_data)
    
    async def _execute_dry_run(self, write_request: HiNATAWriteRequestModel, 
                             session_id: str) -> Dict[str, Any]:
        """执行试运行"""
        
        # 设置试运行标志
        if write_request.bulk_operation:
            write_request.bulk_operation.dry_run = True
        write_request.processing_options["dry_run"] = True
        
        # 创建操作上下文
        context = WriteOperationContext(
            user_id=write_request.user_id,
            operation_id=f"dryrun_{session_id}",
            operation_type=write_request.operation_type,
            intent_description=write_request.intent_description,
            source_app="conversational_interface",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # 执行试运行
        response = await self.write_api.write_processor.process_write_request(write_request, context)
        
        return {
            "estimated_affected": response.affected_count,
            "preview_results": response.results[:5] if response.results else [],
            "warnings": response.warnings,
            "dry_run": True
        }
    
    async def _execute_write_operation(self, write_request: HiNATAWriteRequestModel, 
                                     session: WriteSession) -> Dict[str, Any]:
        """执行实际的写入操作"""
        
        # 关闭试运行模式
        if write_request.bulk_operation:
            write_request.bulk_operation.dry_run = False
        write_request.processing_options["dry_run"] = False
        
        # 创建操作上下文
        context = WriteOperationContext(
            user_id=write_request.user_id,
            operation_id=f"exec_{session.session_id}",
            operation_type=write_request.operation_type,
            intent_description=write_request.intent_description,
            source_app="conversational_interface",
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # 执行写入操作
        response = await self.write_api.write_processor.process_write_request(write_request, context)
        
        return {
            "status": response.status,
            "affected_count": response.affected_count,
            "processing_time": response.processing_time,
            "results": response.results,
            "errors": response.errors,
            "operation_id": response.operation_id
        }
    
    def _apply_user_modifications(self, write_request: HiNATAWriteRequestModel, 
                                modifications: Dict[str, Any]) -> HiNATAWriteRequestModel:
        """应用用户修改"""
        
        # 创建请求副本
        modified_request = write_request.copy(deep=True)
        
        # 应用修改
        if "target_filter" in modifications and modified_request.bulk_operation:
            for key, value in modifications["target_filter"].items():
                modified_request.bulk_operation.target_filter[key] = value
        
        if "operation_data" in modifications and modified_request.bulk_operation:
            for key, value in modifications["operation_data"].items():
                modified_request.bulk_operation.operation_data[key] = value
        
        if "batch_size" in modifications and modified_request.bulk_operation:
            modified_request.bulk_operation.batch_size = modifications["batch_size"]
        
        return modified_request
    
    def _generate_next_steps(self, intent: RecognizedIntent, 
                           preview_results: Optional[Dict[str, Any]]) -> List[str]:
        """生成下一步建议"""
        
        next_steps = []
        
        if preview_results:
            affected_count = preview_results.get("estimated_affected", 0)
            
            if affected_count == 0:
                next_steps.extend([
                    "没有找到匹配的记录",
                    "请检查筛选条件是否正确",
                    "可以尝试修改搜索条件"
                ])
            elif affected_count > 100:
                next_steps.extend([
                    f"将影响 {affected_count} 条记录，数量较多",
                    "建议先缩小操作范围",
                    "或者分批次执行操作"
                ])
            else:
                next_steps.extend([
                    f"预计影响 {affected_count} 条记录",
                    "确认无误后可以执行操作",
                    "操作前会自动创建备份"
                ])
        
        # 根据意图类型添加特定建议
        if intent.intent_type == IntentType.DELETE_HINATA:
            next_steps.append("删除操作将使用软删除，可以恢复")
        elif intent.intent_type in [IntentType.BULK_TAG, IntentType.BULK_RETAG]:
            next_steps.append("标签操作会立即生效，请仔细确认")
        
        return next_steps
    
    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self.app


# 使用示例
async def create_conversational_interface() -> FastAPI:
    """创建和初始化对话式写入接口"""
    config = {
        'redis_url': 'redis://localhost:6379',
        'postgres_dsn': 'postgresql://user:password@localhost/byenatos',
        'cold_storage_path': '/data/cold_storage',
        'chroma_persist_dir': '/data/chroma',
        'elasticsearch_url': 'http://localhost:9200'
    }
    
    interface = ConversationalWriteInterface(config)
    await interface.initialize()
    
    return interface.get_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "InterfaceAbstraction.APIs.ConversationalWriteInterface:create_conversational_interface",
        host="0.0.0.0",
        port=8082,
        reload=True,
        factory=True
    )