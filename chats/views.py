class Create_session(APIView):
       @swagger_auto_schema(
           operation_summary="채팅 생성 API",
           operation_description="Create new chat",
           request_body=CreateSessionSerializer,
           responses ={
               201: openapi.Response(
                   description="채팅 생성 성공",
                   examples={
                        "application/json": {
                            "status" : "success",
                            "code": "COMMON_201",
                            "messages":"새로운 채팅 세션이 생성되었습니다.",
                            "data": {
                                "session_id" : 123,
                                "title": "임대차 계약 관련 상담"

                            }
                        }
                  }
               ),
               401: openapi.Response(
                    description="채팅 메세지가 없어서 채팅 생성 실패",
                    examples={
                        "application/json": {
                            "status" : "error",
                            "code": "ERR_400",
                            "messages" : "첫 메세지가 필요합니다",
                            "data" : null
                       }
                    }
               ),
               404: openapi.Response(
                   description="관련 데이터 못참음",
                    examples={
                        "application/json": {
                            "status" : "error",
                            "code" : "RAG_404",
                            "messages" : "질문하신 내용과 관련된 법률 데이터를 찾지 못했습니다.",
                            "data" : null
                        }
                    }
               ),
               405: openapi.Response(
                   description="지원 하지 않는 메서드",
                   examples={
                        "application/json": {
                            "status" : "error",
                            "code" : "ERR_405",
                            "messages": "지원하지 않는 요청 메서드입니다."
                        }
                    }
               ),
               504: openapi.Response(
                   description="시간 지연 오류",
                   examples={
                       "application/json": {
                           "status" : "error",
                           "code" : "ERR_504",
                           "messages" : "AI 변호사가 분석하는데 시간이 오래 걸리고 있습니다."
                       }

                   }

               )

          }
       )
       def post(self, request, *args, **kwargs):

           messages= request.data.get("messages")

           if not messages:
            response_data ={
                "status": "error",
                "code": "ERR_400",
                "messages" : "첫 메세지가 필요합니다."
            }
            logger.warning(f"{client_ip} POST /sessions 400 BAD Resquest: 필수 데이터 누락")
            return Response(data=response_data, status=status.HTTP_400_BAD_REQUEST)




def patch(self, request, session_id=None, message_id=None):
    target_id = message_id or request.data.get("message_id")
    new_content = request.data.get("message")

    if not target_id or not new_content:
        return Response({"error": "message_id와 message가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # 1. 원본 유저 메시지 객체 가져오기 (삭제되지 않은 것만)
        original_user_msg = get_object_or_404(
            Message, id=target_id, role='user', is_deleted=False
        )
        session = original_user_msg.session

        # 2. 서비스 호출 (삭제 후 새로 생성하는 로직)
        new_ai_msg = ChatService.update_chat_by_replacement(session, original_user_msg, new_content)

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "메시지가 성공적으로 교체되었습니다.",
            "data": AIChatResponseSerializer(new_ai_msg).data
        }, status=status.HTTP_200_OK)

    except Session.DoesNotExist:
        return Response({"status": "error", "message": "세션을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
