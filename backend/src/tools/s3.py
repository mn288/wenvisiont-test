from typing import Optional, Type

import aioboto3
import aiohttp
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from models.infrastructure import S3Config


class S3ListBucketsSchema(BaseModel):
    pass


class AsyncS3ListBucketsTool(BaseTool):
    name: str = "S3 List Buckets (Async)"
    description: str = "Lists all S3 buckets available to the current credentials asynchronously."
    args_schema: Type[BaseModel] = S3ListBucketsSchema
    s3_config: Optional[S3Config] = Field(default=None, exclude=True)

    def __init__(self, s3_config: Optional[S3Config] = None, **kwargs):
        super().__init__(**kwargs)
        self.s3_config = s3_config

    def _get_session(self):
        if self.s3_config:
            return aioboto3.Session(
                aws_access_key_id=self.s3_config.access_key_id,
                aws_secret_access_key=self.s3_config.secret_access_key,
                region_name=self.s3_config.region_name,
            )
        return aioboto3.Session()

    async def _run(self) -> str:
        return await self._arun()

    async def _arun(self) -> str:
        session = self._get_session()
        try:
            async with session.client("s3") as s3:
                response = await s3.list_buckets()
                buckets = [b["Name"] for b in response.get("Buckets", [])]
                return "\n".join(buckets)
        except Exception as e:
            return f"Error listing buckets: {str(e)}"


class S3ReadObjectSchema(BaseModel):
    bucket: str = Field(..., description="The name of the S3 bucket.")
    key: str = Field(..., description="The key (path) of the object to read.")


class AsyncS3ReadTool(BaseTool):
    name: str = "S3 Read Object (Async)"
    description: str = "Reads the content of an object from S3 asynchronously."
    args_schema: Type[BaseModel] = S3ReadObjectSchema
    s3_config: Optional[S3Config] = Field(default=None, exclude=True)

    def __init__(self, s3_config: Optional[S3Config] = None, **kwargs):
        super().__init__(**kwargs)
        self.s3_config = s3_config

    def _get_session(self):
        if self.s3_config:
            return aioboto3.Session(
                aws_access_key_id=self.s3_config.access_key_id,
                aws_secret_access_key=self.s3_config.secret_access_key,
                region_name=self.s3_config.region_name,
            )
        return aioboto3.Session()

    async def _run(self, bucket: str, key: str) -> str:
        return await self._arun(bucket, key)

    async def _arun(self, bucket: str, key: str) -> str:
        session = self._get_session()
        try:
            async with session.client("s3") as s3:
                # Generate presigned URL for getting the object
                url = await s3.generate_presigned_url(
                    ClientMethod="get_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=3600,
                )

                # Fetch content using aiohttp
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.get(url) as response:
                        if response.status != 200:
                            return f"Error reading S3 object: HTTP {response.status} - {await response.text()}"
                        content = await response.read()
                        return content.decode("utf-8")
        except Exception as e:
            return f"Error reading S3 object: {str(e)}"


class S3WriteObjectSchema(BaseModel):
    bucket: str = Field(..., description="The name of the S3 bucket.")
    key: str = Field(..., description="The key (path) where the object will be saved.")
    content: str = Field(..., description="The content to upload.")


class AsyncS3WriteTool(BaseTool):
    name: str = "S3 Write Object (Async)"
    description: str = "Writes content to an S3 object asynchronously."
    args_schema: Type[BaseModel] = S3WriteObjectSchema
    s3_config: Optional[S3Config] = Field(default=None, exclude=True)

    def __init__(self, s3_config: Optional[S3Config] = None, **kwargs):
        super().__init__(**kwargs)
        self.s3_config = s3_config

    def _get_session(self):
        if self.s3_config:
            return aioboto3.Session(
                aws_access_key_id=self.s3_config.access_key_id,
                aws_secret_access_key=self.s3_config.secret_access_key,
                region_name=self.s3_config.region_name,
            )
        return aioboto3.Session()

    async def _run(self, bucket: str, key: str, content: str) -> str:
        return await self._arun(bucket, key, content)

    async def _arun(self, bucket: str, key: str, content: str) -> str:
        session = self._get_session()
        try:
            async with session.client("s3") as s3:
                # Generate presigned URL for putting the object
                url = await s3.generate_presigned_url(
                    ClientMethod="put_object",
                    Params={"Bucket": bucket, "Key": key},
                    ExpiresIn=3600,
                )

                # Upload content using aiohttp
                async with aiohttp.ClientSession() as http_session:
                    async with http_session.put(url, data=content.encode("utf-8")) as response:
                        if response.status not in (200, 201, 204):
                            return f"Error writing S3 object: HTTP {response.status} - {await response.text()}"

            return f"Successfully uploaded to s3://{bucket}/{key}"
        except Exception as e:
            return f"Error writing S3 object: {str(e)}"


class S3DeleteObjectSchema(BaseModel):
    bucket: str = Field(..., description="The name of the S3 bucket.")
    key: str = Field(..., description="The key (path) of the object to delete.")


class AsyncS3DeleteObjectTool(BaseTool):
    name: str = "S3 Delete Object (Async)"
    description: str = "Deletes an S3 object asynchronously."
    args_schema: Type[BaseModel] = S3DeleteObjectSchema
    s3_config: Optional[S3Config] = Field(default=None, exclude=True)

    def __init__(self, s3_config: Optional[S3Config] = None, **kwargs):
        super().__init__(**kwargs)
        self.s3_config = s3_config

    def _get_session(self):
        if self.s3_config:
            return aioboto3.Session(
                aws_access_key_id=self.s3_config.access_key_id,
                aws_secret_access_key=self.s3_config.secret_access_key,
                region_name=self.s3_config.region_name,
            )
        return aioboto3.Session()

    async def _run(self, bucket: str, key: str) -> str:
        return await self._arun(bucket, key)

    async def _arun(self, bucket: str, key: str) -> str:
        session = self._get_session()
        try:
            async with session.client("s3") as s3:
                await s3.delete_object(Bucket=bucket, Key=key)
            return f"Successfully deleted s3://{bucket}/{key}"
        except Exception as e:
            return f"Error deleting S3 object: {str(e)}"


class S3UpdateObjectSchema(BaseModel):
    bucket: str = Field(..., description="The name of the S3 bucket.")
    key: str = Field(..., description="The key (path) of the object to update.")
    content: str = Field(..., description="The content to update.")


class AsyncS3UpdateObjectTool(BaseTool):
    name: str = "S3 Update Object (Async)"
    description: str = "Updates an S3 object asynchronously."
    args_schema: Type[BaseModel] = S3UpdateObjectSchema
    s3_config: Optional[S3Config] = Field(default=None, exclude=True)

    def __init__(self, s3_config: Optional[S3Config] = None, **kwargs):
        super().__init__(**kwargs)
        self.s3_config = s3_config

    def _get_session(self):
        if self.s3_config:
            return aioboto3.Session(
                aws_access_key_id=self.s3_config.access_key_id,
                aws_secret_access_key=self.s3_config.secret_access_key,
                region_name=self.s3_config.region_name,
            )
        return aioboto3.Session()

    async def _run(self, bucket: str, key: str, content: str) -> str:
        return await self._arun(bucket, key, content)

    async def _arun(self, bucket: str, key: str, content: str) -> str:
        session = self._get_session()
        try:
            async with session.client("s3") as s3:
                await s3.put_object(Bucket=bucket, Key=key, Body=content.encode("utf-8"))
            return f"Successfully updated s3://{bucket}/{key}"
        except Exception as e:
            return f"Error updating S3 object: {str(e)}"
