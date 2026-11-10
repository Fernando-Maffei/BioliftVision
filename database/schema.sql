create database [bioliftvisionDB]

USE [bioliftvisionDB]
GO
/****** Object:  Table [dbo].[Analises]    Script Date: 09/12/2025 04:26:33 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Analises](
	[ID_ANALISE] [int] IDENTITY(1,1) NOT NULL,
	[NOTA] [decimal](18, 4) NULL,
	[OBSERVACAO_JUIZ] [nvarchar](max) NULL,
	[DATA_CRIACAO] [datetime2](7) NOT NULL,
	[DATA_ATUALIZACAO] [datetime2](7) NULL,
	[STATUS] [nvarchar](50) NULL,
	[JUIZ] [nvarchar](150) NULL,
	[ATLETA] [nvarchar](150) NULL,
	[EXERCICIO] [nvarchar](100) NULL,
	[TENTATIVA] [int] NULL,
	[AUTO_VALIDO] [bit] NULL,
	[AUTO_RESUMO_JSON] [nvarchar](max) NULL,
	[ANGULOS_JSON] [nvarchar](max) NULL,
PRIMARY KEY CLUSTERED 
(
	[ID_ANALISE] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[Analises_Log]    Script Date: 09/12/2025 04:26:34 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[Analises_Log](
	[LOG_ID] [int] IDENTITY(1,1) NOT NULL,
	[ID_ANALISE] [int] NOT NULL,
	[ACTION] [nvarchar](20) NOT NULL,
	[FIELD_NAME] [nvarchar](128) NULL,
	[OLD_VALUE] [nvarchar](max) NULL,
	[NEW_VALUE] [nvarchar](max) NULL,
	[CHANGED_AT] [datetime2](7) NOT NULL,
	[CHANGED_BY] [nvarchar](150) NULL,
PRIMARY KEY CLUSTERED 
(
	[LOG_ID] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
/****** Object:  Table [dbo].[users]    Script Date: 09/12/2025 04:26:34 ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[users](
	[id] [int] IDENTITY(1,1) NOT NULL,
	[name] [nvarchar](120) NOT NULL,
	[username] [nvarchar](64) NOT NULL,
	[email] [nvarchar](255) NULL,
	[password_hash] [nvarchar](256) NOT NULL,
	[salt] [nvarchar](64) NOT NULL,
	[role] [nvarchar](32) NOT NULL,
	[is_active] [bit] NOT NULL,
	[created_at] [datetime2](7) NOT NULL,
	[is_admin] [bit] NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[username] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
ALTER TABLE [dbo].[Analises] ADD  DEFAULT (sysutcdatetime()) FOR [DATA_CRIACAO]
GO
ALTER TABLE [dbo].[Analises_Log] ADD  DEFAULT (sysutcdatetime()) FOR [CHANGED_AT]
GO
ALTER TABLE [dbo].[users] ADD  DEFAULT ('judge') FOR [role]
GO
ALTER TABLE [dbo].[users] ADD  DEFAULT ((1)) FOR [is_active]
GO
ALTER TABLE [dbo].[users] ADD  DEFAULT (sysutcdatetime()) FOR [created_at]
GO
ALTER TABLE [dbo].[users] ADD  CONSTRAINT [DF_users_is_admin]  DEFAULT ((0)) FOR [is_admin]
GO
ALTER TABLE [dbo].[Analises_Log]  WITH CHECK ADD  CONSTRAINT [FK_AnalisesLog_Analises] FOREIGN KEY([ID_ANALISE])
REFERENCES [dbo].[Analises] ([ID_ANALISE])
GO
ALTER TABLE [dbo].[Analises_Log] CHECK CONSTRAINT [FK_AnalisesLog_Analises]
GO
ALTER TABLE [dbo].[users]  WITH CHECK ADD  CONSTRAINT [CK_users_role_is_admin] CHECK  ((lower([role])='admin' AND [is_admin]=(1) OR lower([role])<>'admin' AND [is_admin]=(0)))
GO
ALTER TABLE [dbo].[users] CHECK CONSTRAINT [CK_users_role_is_admin]
GO
