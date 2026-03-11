from cryptography.fernet import Fernet
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from sqlalchemy import String, BigInteger, Integer,Boolean, Float, ForeignKey,func,select,update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column,relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker,AsyncSession
from datetime import datetime,timedelta
from typing import List,Optional
from discord import Interaction,Message,User,Member,TextChannel,Embed
from pydiscordbio import Client as PydiscordBioClient
import logging
import asyncio
import random
from entities import EntityException
import chromadb

load_dotenv()
SECRET_KEY=os.getenv("SECRET").strip()
cipher_suite=Fernet(SECRET_KEY)
keys=["GEMINI_API"]
DB_PATH="./chroma_db"
# 初始化 ChromaDB
client = chromadb.PersistentClient(path=DB_PATH)
# 建立一個 Collection，並自定義 Embedding 邏輯
collection = client.get_or_create_collection(name="local_kb")

def random_select_key():
    return keys[0]

default_api_key=os.getenv("GEMINI_API")
default_client = genai.Client(api_key=default_api_key)

def encrypt_api_key(raw_data):
    
    cipher_text = cipher_suite.encrypt(raw_data.encode())
    return cipher_text

def decrypt_api_key(byte):
    plain_text = cipher_suite.decrypt(byte).decode()
    return plain_text

def get_models_list()->list:
    return [x.name.split('/')[1] for x in default_client.models.list() if 'generateContent' in x.supported_actions and (x.name.endswith('flash') or x.name.endswith('flash-lite'))]


# 1. 基礎類別
class Base(AsyncAttrs, DeclarativeBase):
    pass

class ChatUsers(Base):
    __tablename__="Users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    token_remaining: Mapped[float] = mapped_column(Float,default=100000.0)
    persona: Mapped[Optional[str]] = mapped_column(String(500),default=None)
    enable_reply: Mapped[bool] = mapped_column(Boolean,default=True)
    using_model: Mapped[str] = mapped_column(String(64),default="gemini-2.0-flash")
    chat_count: Mapped[int] = mapped_column(Integer,default=0)
    api_secret: Mapped[Optional[str]] = mapped_column(String(128),default=None)
    create_at: Mapped[datetime] = mapped_column(server_default=func.now())
    update_at: Mapped[datetime] = mapped_column(server_default=func.now(),onupdate=func.now())
    
    
    sent: Mapped[List["ChatMessages"]] = relationship("ChatMessages",back_populates="author",cascade="all, delete-orphan")
    
    def __repr__(self)->str:
        return f"<User(id={self.id},token_remaining={self.token_remaining})"
        
class ChatMessages(Base):
    __tablename__="Messages"
    message_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    channel_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[int] = mapped_column(ForeignKey("Users.id"))
    role: Mapped[str] = mapped_column(String(8))
    user_name: Mapped[str] = mapped_column(String(128))
    content: Mapped[str] = mapped_column(String(4096))
    reply_to_id: Mapped[int] = mapped_column(Integer)
    token_count: Mapped[float] = mapped_column(Float)
    timestamp:Mapped[datetime] = mapped_column(server_default=func.now())
    
    author: Mapped["ChatUsers"] = relationship("ChatUsers",back_populates="sent")
    
    def __repr__(self)->str:
        return f"<Message(id={self.message_id},content={self.content})"
    
class ChannelContexts(Base):
    __tablename__="Channel_Context"
    
    channel_id: Mapped[int]=mapped_column(BigInteger,primary_key=True)
    last_summary: Mapped[str]=mapped_column(String(1024))
    last_msg_id: Mapped[int]=mapped_column(BigInteger)
    active_topics: Mapped[str]=mapped_column(String(32))
    update_at: Mapped[datetime]=mapped_column(server_default=func.now(),onupdate=func.now())
    
    def __repr__(self)->str:
        return f"<ChannelContext(id={self.channel_id},active_topics={self.active_topics})"

engine = create_async_engine("sqlite+aiosqlite:///chatbot_data.db", echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class ChatUser(): 
    def __init__(self,session: AsyncSession,discord_user:User)->None: 
        self.session= session
        self.user_id=discord_user.id
        self.data: Optional[ChatUsers] = None
        self.client: genai.Client = genai.Client(api_key=default_api_key)
        self.discord_user: User = discord_user
        self.instrucion=f"""
# Role
你是一個整合在 Discord 平台上的專業 AI 助手。你的mention為 <#1406320447343296542>。
# Basic Context (靜態資料交互規範)
你必須根據以下提供的「當前環境資訊」來調整你的回答，這些資訊是實時更新的：
- 當前時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} (請注意時區為 UTC+8)
- 向你發出請求的使用者：{discord_user.mention} ，名稱為 {discord_user.global_name}
# Output Format
- 以繁體中文回答
- 保持簡潔、友善。
- 支援 Markdown 格式（如粗體、代碼塊）。
        """
    
    async def load(self):
        stmt = select(ChatUsers).where(ChatUsers.id == self.user_id)
        result= await self.session.execute(stmt)
        self.data=result.scalar_one_or_none()
        if not self.data:
            # persona_gen=default_client.models.generate_content(
            #     model="gemini-1.5-flash",
            #     contents=f"用戶名稱(Global Name):{self.discord_user.global_name}\n顯示名稱(Display Name): {self.discord_user.display_name}\n用戶自介: {self.discord_user}",
            #     config=types.GenerateContentConfig(
            #         temperature=0.2,
            #         system_instruction="協助分析該Discord用戶的基本資料，分析該用戶的persona(比如興趣、愛好、身分等)，如果用戶的基本資料趨於抽象或不正經，請不要納入分析",
            #         max_output_tokens=2000
            #         )
            #     )
            self.data=ChatUsers(id=self.user_id)
            self.session.add(self.data)
        else:
            utc=datetime.now()-timedelta(hours=8)
            logging.info(f"Last update:{self.data.update_at}, Now:{utc}")
            if utc-self.data.update_at<timedelta(seconds=20):
                return 3
            tokens_left=self.data.token_remaining
            if tokens_left>=100000.0:
                self.data.token_remaining=100000.0
            else:
                delta:timedelta = datetime.now()-self.data.update_at
                self.data.token_remaining=min(100000.0,tokens_left+delta.seconds/60*2.5)
        await self.session.flush()
        return 1
            
    async def set_token(self,amount:float):
        self.data.token_remaining=amount
        await self.session.flush()
    
        
    async def set_api(self,api_key:str):
        self.data.api_secret=encrypt_api_key(api_key)
        await self.session.flush()
        
    @property
    def api_key(self):
        return decrypt_api_key(self.data.api_secret)
        
    
    async def switch_enable_reply(self,enable:bool=None):
        enable_reply=self.data.enable_reply
        if enable is not None:
            self.data.enable_reply=enable
        else:
            self.data.enable_reply=not enable_reply
        await self.session.flush()
    
        
    async def set_model(self,model_name:str):
        if model_name in get_models_list():
            self.data.using_model=model_name
            await self.session.flush()
        else:
            logging.error(f"Model {model_name} is not supported.")
    
    async def update_chat_count(self):
        self.data.chat_count+=1
        await self.session.flush()
        
    
    async def update_persona(self,persona:str):
        self.data.persona=persona
        await self.session.flush()

    
    async def chat(self,content:str):
        if self.data.token_remaining<100:
            return 2,None
        if self.data.api_secret:
            client=genai.Client(api_key=self.api_key)
            using_self_api=True
        else:
            client=self.client
            using_self_api=False
        context=self.query_knowledge_base(content)
        if context:
            final_instruction=self.instrucion+"\n#Retrieval Context\n"+context
        else:
            final_instruction=self.instrucion
        chat:genai.chats.AsyncChat= client.aio.chats.create(model=self.data.using_model)
        response=await chat.send_message(
            message=content,
            config=types.GenerateContentConfig(
                system_instruction=final_instruction,
                max_output_tokens=2000
            ))
        usage = response.usage_metadata
        prompt_tokens = usage.prompt_token_count         # 輸入的 Token (含 Context)
        completion_tokens = usage.candidates_token_count # AI 回答的 Token
        total_tokens = usage.total_token_count           # 總計
        if not using_self_api:
            await self.set_token(max(0,self.data.token_remaining-total_tokens))
        await self.update_chat_count()
        return 1,response.text
    
    def query_knowledge_base(self,user_query,distance_threshold=0.75):
        # 1. 將用戶問題向量化
        response=self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=user_query,
            config={
            "task_type":"retrieval_query"
            }
        )
        query_vec = response.embeddings[0].values

        # 2. 一次取回前 3 名進行判斷
        results = collection.query(
            query_embeddings=[query_vec],
            n_results=3,
            include=['documents', 'distances', 'metadatas']
        )
        
        final_context_chunks = []

        # 3. 逐步判斷相關性
        for i in range(len(results['documents'][0])):
            doc = results['documents'][0][i]
            dist = results['distances'][0][i]
            
            # 如果距離超過閾值，停止加入後續片段
            if dist > distance_threshold:
                logging.info(f"片段 {i+1} 相關度不足 (Distance: {dist:.4f})，停止檢索。")
                break
                
            logging.info(f"匹配片段 {i+1}: Distance {dist:.4f}")
            final_context_chunks.append(doc)
        logging.info(f"Result:{final_context_chunks}")
        return "\n---\n".join(final_context_chunks)
    
async def init_db():
    """初始化資料庫：建立所有資料表"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ 資料庫初始化完成")




async def chat_via_interaction(interaction:Interaction,content:str):
    author:User=interaction.user
    channel:TextChannel=interaction.channel
    if author and channel:
        async with async_session() as session:
            async with session.begin():
                chatuser=ChatUser(session,author)
                load_code = await chatuser.load()
                if load_code==3:
                    raise EntityException("操作太過於頻繁","請稍後再試")
                code,response=await chatuser.chat(content)
                if code==1:
                    await interaction.followup.send(response)
                    return
                if code==2:
                    await interaction.followup.send("❌ 您的Token不足100，不足最低使用要求",ephemeral=True)
                    return
                else:
                    await interaction.followup.send("❌ 發生未知錯誤",ephemeral=True)
                    return
                return
        
    else:
        logging.error("Author or channel info is missing.")
        raise EntityException("Author or channel info is missing.","未知用戶或未知頻道")
    
    
async def chat_via_mention(message:Message):
    user=message.author
    async with async_session() as session:
        async with session.begin():
            chatuser=ChatUser(session,user)
            load_code = await chatuser.load()
            if load_code==3:
                return load_code
            code,response=await chatuser.chat(message.content)
            if code == 1:
                await message.reply(response)
                return
            else:
                return code

async def get_token_remaining(interaction:Interaction):
    user_id=interaction.user.id
    async with async_session() as session:
        async with session.begin():
            chatuser=ChatUser(session,user_id)
            await chatuser.load()
            await interaction.followup.send(embed=Embed(
                title=f"{interaction.user.mention} 的剩餘權杖",
                description=f"剩餘權杖: {chatuser.data.token_remaining:.2f}",
                color=Colour.green()
            ))
            return
        
async def set_gemini_api_key(interaction:Interaction,api_key:str):
    user_id=interaction.user.id
    async with async_session() as session:
        async with session.begin():
            chatuser=ChatUser(session,user_id)
            await chatuser.load()
            await chatuser.set_api(api_key)
            await interaction.followup.send("✅ API Key 設置成功",ephemeral=True)
            return
        
    
asyncio.run(init_db())
