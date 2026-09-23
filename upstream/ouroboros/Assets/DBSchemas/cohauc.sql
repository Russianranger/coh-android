USE [master]
GO
/****** Object:  Database [cohauc]    Script Date: 4/19/2019 11:56:41 PM ******/
CREATE DATABASE [cohauc]
GO
ALTER DATABASE [cohauc] SET COMPATIBILITY_LEVEL = 100
GO
IF (1 = FULLTEXTSERVICEPROPERTY('IsFullTextInstalled'))
begin
EXEC [cohauc].[dbo].[sp_fulltext_database] @action = 'enable'
end
GO
ALTER DATABASE [cohauc] SET ANSI_NULL_DEFAULT OFF 
GO
ALTER DATABASE [cohauc] SET ANSI_NULLS ON 
GO
ALTER DATABASE [cohauc] SET ANSI_PADDING ON 
GO
ALTER DATABASE [cohauc] SET ANSI_WARNINGS OFF 
GO
ALTER DATABASE [cohauc] SET ARITHABORT OFF 
GO
ALTER DATABASE [cohauc] SET AUTO_CLOSE OFF 
GO
ALTER DATABASE [cohauc] SET AUTO_CREATE_STATISTICS ON 
GO
ALTER DATABASE [cohauc] SET AUTO_SHRINK OFF 
GO
ALTER DATABASE [cohauc] SET AUTO_UPDATE_STATISTICS ON 
GO
ALTER DATABASE [cohauc] SET CURSOR_CLOSE_ON_COMMIT OFF 
GO
ALTER DATABASE [cohauc] SET CURSOR_DEFAULT  GLOBAL 
GO
ALTER DATABASE [cohauc] SET CONCAT_NULL_YIELDS_NULL OFF 
GO
ALTER DATABASE [cohauc] SET NUMERIC_ROUNDABORT OFF 
GO
ALTER DATABASE [cohauc] SET QUOTED_IDENTIFIER OFF 
GO
ALTER DATABASE [cohauc] SET RECURSIVE_TRIGGERS OFF 
GO
ALTER DATABASE [cohauc] SET  DISABLE_BROKER 
GO
ALTER DATABASE [cohauc] SET AUTO_UPDATE_STATISTICS_ASYNC OFF 
GO
ALTER DATABASE [cohauc] SET DATE_CORRELATION_OPTIMIZATION OFF 
GO
ALTER DATABASE [cohauc] SET TRUSTWORTHY OFF 
GO
ALTER DATABASE [cohauc] SET ALLOW_SNAPSHOT_ISOLATION OFF 
GO
ALTER DATABASE [cohauc] SET PARAMETERIZATION SIMPLE 
GO
ALTER DATABASE [cohauc] SET READ_COMMITTED_SNAPSHOT OFF 
GO
ALTER DATABASE [cohauc] SET HONOR_BROKER_PRIORITY OFF 
GO
ALTER DATABASE [cohauc] SET RECOVERY FULL 
GO
ALTER DATABASE [cohauc] SET  MULTI_USER 
GO
ALTER DATABASE [cohauc] SET PAGE_VERIFY CHECKSUM  
GO
ALTER DATABASE [cohauc] SET DB_CHAINING OFF 
GO
EXEC sys.sp_db_vardecimal_storage_format N'cohauc', N'ON'
GO
USE [cohauc]
GO
/****** Object:  StoredProcedure [dbo].[SP_delete_ent]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_delete_ent]
	-- Add the parameters for the stored procedure here
	@ent_id int,
	@shard_name varchar(50)
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	DELETE FROM auction_ents WHERE ent_id = @ent_id AND shard_name = @shard_name;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_insert_or_update_ent]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_insert_or_update_ent]
	@ent_id int,
	@shard_name varchar(50),
	@data text
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
	BEGIN TRANSACTION;
	
    UPDATE auction_ents SET data = @data, updated = GETDATE() WHERE [ent_id] = @ent_id AND [shard_name] = @shard_name;
    
    IF @@ROWCOUNT = 0 BEGIN
		INSERT INTO auction_ents ([ent_id], [shard_name], data, updated) VALUES (@ent_id, @shard_name, @data, GETDATE());
    END
    
    COMMIT;
END


GO
/****** Object:  StoredProcedure [dbo].[SP_insert_or_update_history]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_insert_or_update_history]
	@identifier varchar(255),
	@data text
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
	BEGIN TRANSACTION;
	
    UPDATE history SET data = @data WHERE [identifier] = @identifier;
    
    IF @@ROWCOUNT = 0 BEGIN
		INSERT INTO history ([identifier], data) VALUES (@identifier, @data);
    END
    
    COMMIT;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_insert_shard]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_insert_shard]
	@data text
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
	BEGIN TRANSACTION;

	INSERT INTO shards (data) VALUES (@data);

    COMMIT;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_write_ents_crc]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_write_ents_crc]
	-- Add the parameters for the stored procedure here
	@crc int
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	UPDATE parse_versions set ents_crc = @crc;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_write_history_crc]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_write_history_crc]
	-- Add the parameters for the stored procedure here
	@crc int
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	UPDATE parse_versions set history_crc = @crc;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_write_shards_crc]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_write_shards_crc]
	-- Add the parameters for the stored procedure here
	@crc int
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	UPDATE parse_versions set shards_crc = @crc;
END

GO
/****** Object:  Table [dbo].[auction_ents]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[auction_ents](
	[ent_id] [int] NOT NULL,
	[shard_name] [varchar](50) NOT NULL,
	[data] [text] NULL,
	[updated] [datetime] NOT NULL,
 CONSTRAINT [PK_ents] PRIMARY KEY CLUSTERED 
(
	[ent_id] ASC,
	[shard_name] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[history]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[history](
	[identifier] [varchar](255) NOT NULL,
	[data] [text] NULL,
 CONSTRAINT [PK_history] PRIMARY KEY CLUSTERED 
(
	[identifier] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

GO
SET ANSI_PADDING OFF
GO
/****** Object:  Table [dbo].[parse_versions]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[parse_versions](
	[shards_crc] [int] NULL,
	[ents_crc] [int] NULL,
	[history_crc] [int] NULL
) ON [PRIMARY]
GO
INSERT [dbo].[parse_versions] ([shards_crc], [ents_crc], [history_crc]) VALUES (0, 0, 0)
GO
/****** Object:  Table [dbo].[shards]    Script Date: 4/19/2019 11:56:41 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[shards](
	[data] [text] NOT NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

GO
/****** Object:  Index [IX_ents]    Script Date: 4/19/2019 11:56:41 PM ******/
CREATE NONCLUSTERED INDEX [IX_ents] ON [dbo].[auction_ents]
(
	[ent_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
SET ANSI_PADDING ON

GO
/****** Object:  Index [IX_ents_1]    Script Date: 4/19/2019 11:56:41 PM ******/
CREATE NONCLUSTERED INDEX [IX_ents_1] ON [dbo].[auction_ents]
(
	[shard_name] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
ALTER TABLE [dbo].[auction_ents] ADD  DEFAULT ('1-1-1970') FOR [updated]
GO
USE [master]
GO
ALTER DATABASE [cohauc] SET  READ_WRITE 
GO
