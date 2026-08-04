"""Especificação OpenAPI 3.0 da API REST (consumida pelo Swagger UI)."""

TICKET_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "number": {"type": "string", "example": "CH-2026-00001"},
        "title": {"type": "string"},
        "category": {"type": "string"},
        "priority": {"type": "string", "enum": ["Baixa", "Média", "Alta", "Crítica"]},
        "status": {
            "type": "string",
            "enum": ["Aberto", "Em andamento", "Aguardando usuário", "Resolvido", "Fechado"],
        },
        "requester": {"type": "object"},
        "assignee": {"type": "object", "nullable": True},
        "created_at": {"type": "string", "format": "date-time"},
        "sla": {"type": "string", "enum": ["ok", "at_risk", "expired", "met", "breached", "none"]},
    },
}


def build_spec():
    """Monta o documento OpenAPI 3.0 da API v1."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Service Desk API",
            "version": "1.0.0",
            "description": (
                "API REST do sistema de chamados. Obtenha um token em "
                "`POST /api/v1/auth/token` e envie-o no header "
                "`Authorization: Bearer <token>`."
            ),
        },
        "servers": [{"url": "/api/v1"}],
        "components": {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"}
            },
            "schemas": {"Ticket": TICKET_SCHEMA},
        },
        "security": [{"bearerAuth": []}],
        "paths": {
            "/auth/token": {
                "post": {
                    "summary": "Obter token de acesso",
                    "security": [],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["email", "password"],
                                    "properties": {
                                        "email": {"type": "string", "example": "admin@empresa.com"},
                                        "password": {"type": "string", "example": "Senha@123"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {"description": "Token gerado"},
                        "401": {"description": "Credenciais inválidas"},
                    },
                }
            },
            "/tickets": {
                "get": {
                    "summary": "Listar chamados",
                    "parameters": [
                        {"name": "page", "in": "query", "schema": {"type": "integer"}},
                        {"name": "per_page", "in": "query", "schema": {"type": "integer", "maximum": 100}},
                        {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Busca em título, descrição e número"},
                        {"name": "status", "in": "query", "schema": {"type": "string"}},
                        {"name": "prioridade", "in": "query", "schema": {"type": "string"}},
                        {"name": "categoria", "in": "query", "schema": {"type": "integer"}},
                    ],
                    "responses": {
                        "200": {
                            "description": "Lista paginada",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "items": {"type": "array", "items": {"$ref": "#/components/schemas/Ticket"}},
                                            "page": {"type": "integer"},
                                            "pages": {"type": "integer"},
                                            "total": {"type": "integer"},
                                        },
                                    }
                                }
                            },
                        }
                    },
                },
                "post": {
                    "summary": "Abrir chamado",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["title", "description", "category_id"],
                                    "properties": {
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "category_id": {"type": "integer"},
                                        "subcategory_id": {"type": "integer"},
                                        "priority": {"type": "string", "enum": ["Baixa", "Média", "Alta", "Crítica"]},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "201": {"description": "Chamado criado"},
                        "400": {"description": "Dados inválidos"},
                    },
                },
            },
            "/tickets/{ticket_id}": {
                "parameters": [
                    {"name": "ticket_id", "in": "path", "required": True, "schema": {"type": "integer"}}
                ],
                "get": {
                    "summary": "Detalhar chamado",
                    "responses": {
                        "200": {"description": "Chamado completo (com comentários)"},
                        "403": {"description": "Sem permissão"},
                        "404": {"description": "Não encontrado"},
                    },
                },
                "patch": {
                    "summary": "Atualizar chamado (equipe)",
                    "description": "Permite alterar status, atribuir analista, comentar e editar campos.",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "status": {"type": "string"},
                                        "solution": {"type": "string"},
                                        "assignee_id": {"type": "integer"},
                                        "comment": {"type": "string"},
                                        "is_internal": {"type": "boolean"},
                                        "title": {"type": "string"},
                                        "description": {"type": "string"},
                                        "priority": {"type": "string"},
                                    },
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Chamado atualizado"},
                        "403": {"description": "Apenas equipe de atendimento"},
                    },
                },
            },
            "/categories": {
                "get": {
                    "summary": "Listar categorias e subcategorias",
                    "responses": {"200": {"description": "Lista de categorias"}},
                }
            },
            "/kb": {
                "get": {
                    "summary": "Buscar na base de conhecimento",
                    "parameters": [
                        {"name": "q", "in": "query", "schema": {"type": "string"}}
                    ],
                    "responses": {"200": {"description": "Artigos publicados"}},
                }
            },
        },
    }
