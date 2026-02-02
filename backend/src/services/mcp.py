from typing import List, Optional

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.database import async_session_maker
from models.mcp import MCPServer, MCPServerCreate


class MCPService:
    async def get_all_servers(self, session: Optional[AsyncSession] = None) -> List[MCPServer]:
        """Fetch all MCP servers from the database."""
        if session:
            return await self._get_all_servers_exec(session)

        async with async_session_maker() as session:
            return await self._get_all_servers_exec(session)

    async def _get_all_servers_exec(self, session: AsyncSession) -> List[MCPServer]:
        statement = select(MCPServer).order_by(MCPServer.name)
        result = await session.exec(statement)
        return list(result.all())

    async def get_servers_by_names(self, names: List[str], session: Optional[AsyncSession] = None) -> List[MCPServer]:
        """Fetch specific MCP servers by name."""
        if not names:
            return []

        if session:
            return await self._get_servers_by_names_exec(names, session)

        async with async_session_maker() as session:
            return await self._get_servers_by_names_exec(names, session)

    async def _get_servers_by_names_exec(self, names: List[str], session: AsyncSession) -> List[MCPServer]:
        statement = select(MCPServer).where(MCPServer.name.in_(names))
        result = await session.exec(statement)
        return list(result.all())

    async def _verify_server(self, server: MCPServerCreate):
        """
        Verify that the MCP server is reachable and valid.
        Raises ValueError if verification fails.
        """
        from fastmcp import Client

        # Determine Client based on type
        try:
            if server.type == "stdio":
                if not server.command:
                    raise ValueError("Command required for stdio")
                client = Client(server.command, args=server.args or [], env=server.env)
            elif server.type in ["sse", "https"]:
                if not server.url:
                    raise ValueError("URL required for sse/https")
                client = Client(server.url)
            else:
                raise ValueError(f"Unknown server type: {server.type}")

            # Attempt connection and listing
            async with client:
                await client.list_tools()

        except Exception as e:
            raise ValueError(f"Verification Failed: Could not connect to MCP server '{server.name}'. Error: {str(e)}")

    async def create_server(self, server: MCPServerCreate, session: Optional[AsyncSession] = None) -> MCPServer:
        """Create a new MCP server in the database."""
        # 1. Verify Connectivity First
        await self._verify_server(server)

        if session:
            return await self._create_server_exec(server, session)

        async with async_session_maker() as session:
            return await self._create_server_exec(server, session)

    async def _create_server_exec(self, server: MCPServerCreate, session: AsyncSession) -> MCPServer:
        # Check duplication
        statement = select(MCPServer).where(MCPServer.name == server.name)
        existing = await session.exec(statement)
        if existing.first():
            raise ValueError(f"MCP Server '{server.name}' already exists")

        # Create DB Model
        db_server = MCPServer.model_validate(server)

        # Manually ensure env is set correctly if needed (pydantic handles it mostly)
        # But for SQLModel/Pydantic, we rely on the model.

        session.add(db_server)
        await session.commit()
        await session.refresh(db_server)
        return db_server

    async def delete_server(self, name: str, session: Optional[AsyncSession] = None) -> bool:
        """Delete an MCP server by name."""
        if session:
            return await self._delete_server_exec(name, session)

        async with async_session_maker() as session:
            return await self._delete_server_exec(name, session)

    async def _delete_server_exec(self, name: str, session: AsyncSession) -> bool:
        statement = select(MCPServer).where(MCPServer.name == name)
        results = await session.exec(statement)
        server = results.first()

        if not server:
            return False

        await session.delete(server)
        await session.commit()
        return True


# Global Instance
mcp_service = MCPService()


def get_mcp_service() -> MCPService:
    """Singleton accessor for MCPService."""
    return mcp_service
