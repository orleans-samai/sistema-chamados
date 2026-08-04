"""Carga inicial do banco: `flask --app run.py seed`.

Cria perfis, usuários de demonstração, departamentos, categorias,
regras de SLA, chamados de exemplo, artigos da base de conhecimento e
cenários do laboratório de treinamento.
"""
from datetime import datetime, timedelta

import click

from app.extensions import db
from app.models import (
    Category,
    Department,
    KnowledgeArticle,
    LabScenario,
    Role,
    SLARule,
    Subcategory,
    Ticket,
    TicketComment,
    TicketHistory,
    TicketPriority,
    TicketStatus,
    User,
)
from app.services.sla_service import apply_sla

DEFAULT_PASSWORD = "Senha@123"


def register_cli(app):
    @app.cli.command("seed")
    def seed_command():
        """Popula o banco com dados de demonstração."""
        if Role.query.first():
            click.echo("Banco já populado — nada a fazer.")
            return
        run_seed()
        click.echo("Seed concluído com sucesso.")
        click.echo(f"Login: admin@empresa.com / {DEFAULT_PASSWORD}")


def run_seed():
    roles = _roles()
    departments = _departments()
    users = _users(roles, departments)
    categories = _categories()
    _sla_rules()
    db.session.commit()  # garante ids para os relacionamentos abaixo

    _tickets(users, categories)
    _knowledge(users, categories)
    _lab_scenarios(users, categories)
    db.session.commit()


def _roles():
    roles = {
        Role.ADMIN: Role(name=Role.ADMIN, description="Acesso total ao sistema"),
        Role.ANALISTA: Role(name=Role.ANALISTA, description="Atende e resolve chamados"),
        Role.USUARIO: Role(name=Role.USUARIO, description="Abre e acompanha chamados"),
    }
    db.session.add_all(roles.values())
    return roles


def _departments():
    departments = {
        name: Department(name=name, description=desc)
        for name, desc in [
            ("TI", "Tecnologia da Informação"),
            ("RH", "Recursos Humanos"),
            ("Financeiro", "Contas a pagar e receber"),
            ("Comercial", "Vendas e atendimento ao cliente"),
        ]
    }
    db.session.add_all(departments.values())
    return departments


def _users(roles, departments):
    spec = [
        ("Administrador do Sistema", "admin@empresa.com", Role.ADMIN, "TI"),
        ("Carlos Andrade", "carlos.analista@empresa.com", Role.ANALISTA, "TI"),
        ("Fernanda Lima", "fernanda.analista@empresa.com", Role.ANALISTA, "TI"),
        ("João Pereira", "joao@empresa.com", Role.USUARIO, "Financeiro"),
        ("Maria Souza", "maria@empresa.com", Role.USUARIO, "RH"),
        ("Pedro Santos", "pedro@empresa.com", Role.USUARIO, "Comercial"),
    ]
    users = {}
    for name, email, role, dept in spec:
        user = User(
            name=name,
            email=email,
            role=roles[role],
            department=departments[dept],
            active=True,
        )
        user.set_password(DEFAULT_PASSWORD)
        user.generate_api_token()
        db.session.add(user)
        users[email] = user
    return users


def _categories():
    spec = {
        "Hardware": ["Computador", "Monitor", "Periféricos"],
        "Software": ["Instalação", "Erro de aplicação", "Atualização"],
        "Redes": ["Sem conexão", "Lentidão", "VPN", "Wi-Fi"],
        "Impressoras": ["Não imprime", "Atolamento de papel", "Tóner"],
        "Microsoft 365": ["Outlook", "Teams", "OneDrive", "Licenciamento"],
        "Acessos": ["Criação de conta", "Reset de senha", "Permissões"],
        "Treinamento": ["Simulado"],
    }
    categories = {}
    for name, subs in spec.items():
        category = Category(name=name)
        db.session.add(category)
        for sub in subs:
            category.subcategories.append(Subcategory(name=sub))
        categories[name] = category
    return categories


def _sla_rules():
    spec = [
        (TicketPriority.CRITICA, 15, 4 * 60, "Parada total de serviço essencial"),
        (TicketPriority.ALTA, 30, 8 * 60, "Impacto severo em um setor"),
        (TicketPriority.MEDIA, 2 * 60, 24 * 60, "Impacto moderado, há alternativa"),
        (TicketPriority.BAIXA, 4 * 60, 72 * 60, "Dúvidas e solicitações sem urgência"),
    ]
    for priority, response, resolution, desc in spec:
        db.session.add(
            SLARule(
                priority=priority,
                response_minutes=response,
                resolution_minutes=resolution,
                description=desc,
            )
        )


def _make_ticket(seq, users, categories, *, title, description, category, sub=None,
                 priority, status, requester, assignee=None, days_ago=0, hours=2,
                 solution=None, rating=None):
    """Cria um chamado retroativo com SLA e histórico coerentes."""
    created = datetime.now() - timedelta(days=days_ago, hours=3)
    category_obj = categories[category]
    sub_obj = next((s for s in category_obj.subcategories if s.name == sub), None)

    ticket = Ticket(
        title=title,
        description=description,
        category_id=category_obj.id,
        subcategory_id=sub_obj.id if sub_obj else None,
        priority=priority,
        status=status,
        requester_id=users[requester].id,
        assignee_id=users[assignee].id if assignee else None,
        created_at=created,
        updated_at=created,
    )
    apply_sla(ticket)
    db.session.add(ticket)
    db.session.flush()
    ticket.number = f"CH-{created.year}-{ticket.id:05d}"

    db.session.add(TicketHistory(
        ticket_id=ticket.id, user_id=users[requester].id,
        action="Chamado criado", created_at=created,
    ))
    if assignee:
        ticket.first_response_at = created + timedelta(minutes=20)
        db.session.add(TicketHistory(
            ticket_id=ticket.id, user_id=users[assignee].id,
            action="Analista atribuído", field="Analista",
            new_value=users[assignee].name,
            created_at=created + timedelta(minutes=15),
        ))
        db.session.add(TicketComment(
            ticket_id=ticket.id, user_id=users[assignee].id,
            content="Olá! Estou verificando o seu chamado.",
            created_at=created + timedelta(minutes=20),
        ))
    if status in (TicketStatus.RESOLVIDO, TicketStatus.FECHADO):
        resolved = created + timedelta(hours=hours)
        ticket.resolved_at = resolved
        ticket.solution = solution or "Problema corrigido e validado com o usuário."
        db.session.add(TicketHistory(
            ticket_id=ticket.id, user_id=users[assignee].id if assignee else None,
            action="Status alterado", field="Status",
            old_value=TicketStatus.EM_ANDAMENTO, new_value=status,
            created_at=resolved,
        ))
        if status == TicketStatus.FECHADO:
            ticket.closed_at = resolved + timedelta(hours=1)
        if rating:
            ticket.rating = rating
    return ticket


def _tickets(users, categories):
    T, P = TicketStatus, TicketPriority
    samples = [
        dict(title="Computador não liga", description="O desktop da recepção não dá vídeo nem sinal de energia. Já testei outra tomada.",
             category="Hardware", sub="Computador", priority=P.ALTA, status=T.FECHADO,
             requester="joao@empresa.com", assignee="carlos.analista@empresa.com",
             days_ago=85, hours=5, rating=5,
             solution="Fonte de alimentação substituída. Equipamento testado e entregue."),
        dict(title="Erro ao abrir o sistema financeiro", description="Ao abrir o ERP aparece a mensagem 'runtime error 503'.",
             category="Software", sub="Erro de aplicação", priority=P.CRITICA, status=T.FECHADO,
             requester="joao@empresa.com", assignee="fernanda.analista@empresa.com",
             days_ago=70, hours=3, rating=4,
             solution="Serviço do banco de dados reiniciado e patch do ERP aplicado."),
        dict(title="Sem acesso à VPN em home office", description="Não consigo conectar na VPN desde ontem à noite. Erro 809.",
             category="Redes", sub="VPN", priority=P.ALTA, status=T.RESOLVIDO,
             requester="maria@empresa.com", assignee="carlos.analista@empresa.com",
             days_ago=45, hours=6, rating=5,
             solution="Cliente VPN reinstalado e credenciais ressincronizadas no firewall."),
        dict(title="Impressora do 2º andar atolando papel", description="A multifuncional atola papel em todas as impressões frente e verso.",
             category="Impressoras", sub="Atolamento de papel", priority=P.MEDIA, status=T.FECHADO,
             requester="pedro@empresa.com", assignee="fernanda.analista@empresa.com",
             days_ago=40, hours=20, rating=3,
             solution="Rolete de tração trocado pela assistência. Testes OK."),
        dict(title="Outlook não sincroniza e-mails", description="Os e-mails novos só aparecem no celular, o Outlook do desktop parou de atualizar.",
             category="Microsoft 365", sub="Outlook", priority=P.MEDIA, status=T.RESOLVIDO,
             requester="maria@empresa.com", assignee="carlos.analista@empresa.com",
             days_ago=22, hours=4, rating=4,
             solution="Perfil do Outlook recriado e OST regenerado."),
        dict(title="Solicitação de acesso à pasta do Financeiro", description="Preciso de acesso de leitura à pasta \\\\servidor\\financeiro para fechar o relatório mensal.",
             category="Acessos", sub="Permissões", priority=P.BAIXA, status=T.FECHADO,
             requester="pedro@empresa.com", assignee="fernanda.analista@empresa.com",
             days_ago=15, hours=26, rating=5,
             solution="Acesso de leitura concedido via grupo do AD, aprovado pelo gestor."),
        dict(title="Teams sem áudio nas reuniões", description="Nas chamadas do Teams ninguém me ouve, o microfone funciona em outros aplicativos.",
             category="Microsoft 365", sub="Teams", priority=P.MEDIA, status=T.EM_ANDAMENTO,
             requester="joao@empresa.com", assignee="carlos.analista@empresa.com", days_ago=2),
        dict(title="Internet lenta no setor Comercial", description="Páginas demoram a abrir e o sistema de vendas trava desde segunda-feira.",
             category="Redes", sub="Lentidão", priority=P.ALTA, status=T.EM_ANDAMENTO,
             requester="pedro@empresa.com", assignee="fernanda.analista@empresa.com", days_ago=1),
        dict(title="Monitor piscando", description="O monitor pisca intermitentemente, principalmente ao abrir planilhas.",
             category="Hardware", sub="Monitor", priority=P.BAIXA, status=T.AGUARDANDO,
             requester="maria@empresa.com", assignee="carlos.analista@empresa.com", days_ago=3),
        dict(title="Instalação do Power BI", description="Preciso do Power BI Desktop instalado para os dashboards da diretoria.",
             category="Software", sub="Instalação", priority=P.MEDIA, status=T.ABERTO,
             requester="pedro@empresa.com", days_ago=0),
        dict(title="Reset de senha do sistema de ponto", description="Esqueci a senha do sistema de ponto e bloqueou após 3 tentativas.",
             category="Acessos", sub="Reset de senha", priority=P.ALTA, status=T.ABERTO,
             requester="maria@empresa.com", days_ago=0),
        dict(title="Wi-Fi do auditório fora do ar", description="O access point do auditório aparece sem internet. Evento marcado para amanhã!",
             category="Redes", sub="Wi-Fi", priority=P.CRITICA, status=T.ABERTO,
             requester="joao@empresa.com", days_ago=0),
    ]
    for sample in samples:
        _make_ticket(0, users, categories, **sample)


def _knowledge(users, categories):
    author = users["carlos.analista@empresa.com"]
    articles = [
        dict(title="Como conectar à VPN corporativa",
             article_type=KnowledgeArticle.TIPO_TUTORIAL, category="Redes",
             tags="vpn, home office, acesso remoto",
             summary="Passo a passo de instalação e conexão do cliente VPN.",
             content="1. Baixe o cliente VPN no portal interno.\n2. Instale com as opções padrão.\n3. Abra o cliente e informe o servidor vpn.empresa.com.\n4. Use seu usuário e senha de rede.\n5. Em caso de erro 809, verifique se a porta 500/4500 UDP está liberada no roteador.\n\nSe o problema persistir, abra um chamado na categoria Redes > VPN."),
        dict(title="Mapear impressora de rede no Windows",
             article_type=KnowledgeArticle.TIPO_TUTORIAL, category="Impressoras",
             tags="impressora, windows, mapeamento",
             summary="Como adicionar uma impressora de rede no Windows 10/11.",
             content="1. Abra Configurações > Bluetooth e dispositivos > Impressoras e scanners.\n2. Clique em Adicionar dispositivo.\n3. Selecione a impressora do seu andar (ex.: IMP-2AND-01).\n4. Caso não apareça, clique em 'Adicionar manualmente' e informe \\\\printserver\\IMP-2AND-01.\n5. Imprima uma página de teste."),
        dict(title="Outlook não sincroniza: checklist rápido",
             article_type=KnowledgeArticle.TIPO_ARTIGO, category="Microsoft 365",
             tags="outlook, e-mail, sincronização",
             summary="Verificações antes de abrir chamado de Outlook.",
             content="• Verifique se há conexão com a internet.\n• Confira o ícone 'Trabalhando offline' na barra inferior do Outlook.\n• Feche e reabra o Outlook.\n• Teste o webmail (outlook.office.com): se funcionar, o problema é local.\n• Reinicie o computador.\n\nSe nada resolver, abra um chamado em Microsoft 365 > Outlook informando a mensagem de erro."),
        dict(title="FAQ — Redefinição de senhas",
             article_type=KnowledgeArticle.TIPO_FAQ, category="Acessos",
             tags="senha, reset, bloqueio",
             summary="Perguntas frequentes sobre senhas e bloqueio de conta.",
             content="P: Esqueci minha senha de rede. O que faço?\nR: Use o portal de autoatendimento ou abra um chamado em Acessos > Reset de senha.\n\nP: Minha conta bloqueou após tentativas erradas.\nR: O desbloqueio é automático após 15 minutos, ou imediato via chamado.\n\nP: Posso repetir senhas antigas?\nR: Não. A política exige senha nova com no mínimo 12 caracteres."),
        dict(title="Boas práticas de segurança da informação",
             article_type=KnowledgeArticle.TIPO_ARTIGO, category="Acessos",
             tags="segurança, phishing, senha",
             summary="Recomendações essenciais para o dia a dia.",
             content="• Desconfie de e-mails com urgência excessiva ou anexos inesperados (phishing).\n• Nunca compartilhe sua senha — a TI jamais pedirá por telefone ou e-mail.\n• Bloqueie a estação ao se ausentar (Win + L).\n• Use o gerenciador de senhas corporativo.\n• Reporte incidentes imediatamente pelo chamado de Segurança."),
        dict(title="Teams sem áudio: como resolver",
             article_type=KnowledgeArticle.TIPO_TUTORIAL, category="Microsoft 365",
             tags="teams, áudio, microfone",
             summary="Configurando o dispositivo de áudio correto no Teams.",
             content="1. No Teams, clique em ... > Configurações > Dispositivos.\n2. Em Microfone, selecione o dispositivo correto (ex.: Headset USB).\n3. Faça uma chamada de teste.\n4. Verifique também as permissões do Windows: Configurações > Privacidade > Microfone.\n5. Atualize o Teams se o problema persistir."),
    ]
    for data in articles:
        category = categories[data.pop("category")]
        db.session.add(
            KnowledgeArticle(category_id=category.id, author_id=author.id, **data)
        )


def _lab_scenarios(users, categories):
    admin = users["admin@empresa.com"]
    scenarios = [
        dict(title="Usuário sem acesso à internet (cabo)", area="Redes", level="N1",
             priority=TicketPriority.ALTA, category="Redes",
             description="Usuário relata que o computador está 'sem internet'. O ícone de rede mostra um X vermelho. Outros colegas do mesmo setor navegam normalmente.",
             expected_solution="Verificar cabo de rede conectado (ambas as pontas), testar outra porta do switch, validar luz do link na placa, executar ipconfig para conferir IP válido (descartar APIPA 169.254.x.x). Causa esperada: cabo desconectado da tomada de parede.",
             hints="Comece pelo físico: cabo, link, depois ipconfig."),
        dict(title="Perfil do Windows corrompido", area="Windows", level="N2",
             priority=TicketPriority.ALTA, category="Software",
             description="Ao fazer logon, o usuário recebe 'O serviço de perfil de usuário falhou no logon' e entra com perfil temporário.",
             expected_solution="Fazer backup dos dados do perfil, corrigir no registro (HKLM\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\ProfileList — remover sufixo .bak), ou recriar o perfil. Validar GPOs aplicadas após logon.",
             hints="Investigue a chave ProfileList no registro."),
        dict(title="Fila de impressão travada", area="Impressoras", level="N1",
             priority=TicketPriority.MEDIA, category="Impressoras",
             description="Nenhum documento sai na impressora do setor. A fila mostra 8 documentos 'imprimindo' há horas.",
             expected_solution="Cancelar trabalhos presos, reiniciar o serviço Spooler de Impressão (services.msc ou net stop/start spooler), limpar a pasta C:\\Windows\\System32\\spool\\PRINTERS e testar página de teste.",
             hints="O serviço de spooler é o principal suspeito."),
        dict(title="Caixa de correio cheia no Exchange Online", area="Microsoft 365", level="N1",
             priority=TicketPriority.MEDIA, category="Microsoft 365",
             description="Usuário não envia nem recebe e-mails. Mensagem: 'caixa de correio excedeu a cota'.",
             expected_solution="Orientar limpeza de Itens Enviados/Excluídos, esvaziar Lixeira, ativar arquivo morto online (In-Place Archive) no admin center e/ou aplicar política de retenção. Conferir cota no Microsoft 365 admin center.",
             hints="Pense em arquivo morto e políticas de retenção."),
        dict(title="Conta bloqueada repetidamente no AD", area="Active Directory", level="N2",
             priority=TicketPriority.ALTA, category="Acessos",
             description="A conta do usuário bloqueia sozinha a cada 10 minutos, mesmo após desbloqueio e troca de senha.",
             expected_solution="Usar LockoutStatus/Get-ADUser para achar o DC de origem, analisar evento 4740 no DC, identificar dispositivo com credencial antiga (celular com Wi-Fi corporativo, unidade mapeada, tarefa agendada ou serviço) e atualizar a senha salva.",
             hints="Evento 4740 no controlador de domínio mostra a origem do bloqueio."),
        dict(title="Suspeita de phishing com anexo malicioso", area="Segurança da informação", level="N2",
             priority=TicketPriority.CRITICA, category="Acessos",
             description="Usuário clicou em link de e-mail 'do banco' e digitou a senha corporativa. Depois percebeu que o remetente era falso.",
             expected_solution="Isolar a estação da rede, resetar a senha imediatamente e revogar sessões/tokens, verificar regras de caixa de correio criadas pelo atacante, analisar logs de acesso (sign-in logs), notificar o time de segurança e registrar o incidente. Orientar o usuário sobre phishing.",
             hints="Contenção primeiro: senha, sessões e regras de e-mail."),
        dict(title="Computador lento ao iniciar", area="Suporte técnico", level="N1",
             priority=TicketPriority.BAIXA, category="Hardware",
             description="Usuário reclama que o computador demora mais de 10 minutos para ficar utilizável após ligar.",
             expected_solution="Verificar programas na inicialização (Gerenciador de Tarefas > Inicializar), checar espaço em disco e saúde do HD (considerar upgrade para SSD), rodar verificação de malware e conferir atualizações pendentes do Windows.",
             hints="Inicialização, disco e malware são os três clássicos."),
    ]
    for data in scenarios:
        category = categories[data.pop("category")]
        db.session.add(
            LabScenario(category_id=category.id, created_by_id=admin.id, active=True, **data)
        )
