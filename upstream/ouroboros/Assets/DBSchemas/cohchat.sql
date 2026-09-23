USE [master]
GO
/****** Object:  Database [cohchat]    Script Date: 4/19/2019 11:57:53 PM ******/
CREATE DATABASE [cohchat]
GO
ALTER DATABASE [cohchat] SET COMPATIBILITY_LEVEL = 100
GO
IF (1 = FULLTEXTSERVICEPROPERTY('IsFullTextInstalled'))
begin
EXEC [cohchat].[dbo].[sp_fulltext_database] @action = 'enable'
end
GO
ALTER DATABASE [cohchat] SET ANSI_NULL_DEFAULT OFF 
GO
ALTER DATABASE [cohchat] SET ANSI_NULLS ON 
GO
ALTER DATABASE [cohchat] SET ANSI_PADDING ON 
GO
ALTER DATABASE [cohchat] SET ANSI_WARNINGS OFF 
GO
ALTER DATABASE [cohchat] SET ARITHABORT OFF 
GO
ALTER DATABASE [cohchat] SET AUTO_CLOSE OFF 
GO
ALTER DATABASE [cohchat] SET AUTO_SHRINK OFF 
GO
ALTER DATABASE [cohchat] SET AUTO_UPDATE_STATISTICS ON 
GO
ALTER DATABASE [cohchat] SET CURSOR_CLOSE_ON_COMMIT OFF 
GO
ALTER DATABASE [cohchat] SET CURSOR_DEFAULT  GLOBAL 
GO
ALTER DATABASE [cohchat] SET CONCAT_NULL_YIELDS_NULL OFF 
GO
ALTER DATABASE [cohchat] SET NUMERIC_ROUNDABORT OFF 
GO
ALTER DATABASE [cohchat] SET QUOTED_IDENTIFIER OFF 
GO
ALTER DATABASE [cohchat] SET RECURSIVE_TRIGGERS OFF 
GO
ALTER DATABASE [cohchat] SET  DISABLE_BROKER 
GO
ALTER DATABASE [cohchat] SET AUTO_UPDATE_STATISTICS_ASYNC OFF 
GO
ALTER DATABASE [cohchat] SET DATE_CORRELATION_OPTIMIZATION OFF 
GO
ALTER DATABASE [cohchat] SET TRUSTWORTHY OFF 
GO
ALTER DATABASE [cohchat] SET ALLOW_SNAPSHOT_ISOLATION OFF 
GO
ALTER DATABASE [cohchat] SET PARAMETERIZATION SIMPLE 
GO
ALTER DATABASE [cohchat] SET READ_COMMITTED_SNAPSHOT OFF 
GO
ALTER DATABASE [cohchat] SET HONOR_BROKER_PRIORITY OFF 
GO
ALTER DATABASE [cohchat] SET RECOVERY FULL 
GO
ALTER DATABASE [cohchat] SET  MULTI_USER 
GO
ALTER DATABASE [cohchat] SET PAGE_VERIFY CHECKSUM  
GO
ALTER DATABASE [cohchat] SET DB_CHAINING OFF 
GO
EXEC sys.sp_db_vardecimal_storage_format N'cohchat', N'ON'
GO
USE [cohchat]
GO
/****** Object:  StoredProcedure [dbo].[SP_delete_channel]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_delete_channel]
	-- Add the parameters for the stored procedure here
	@name varchar(32)
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	DELETE FROM channels WHERE name = @name;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_insert_or_update_channel]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_insert_or_update_channel]
	@name varchar(32),
	@data text
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
	BEGIN TRANSACTION;
	
    UPDATE channels SET data = @data WHERE name = @name;
    
    IF @@ROWCOUNT = 0 BEGIN
		INSERT INTO channels (name, data) VALUES (@name, @data);
    END
    
    COMMIT;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_insert_or_update_user]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_insert_or_update_user]
	@user_id int,
	@data text
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
	BEGIN TRANSACTION;
	
    UPDATE users SET data = @data WHERE [user_id] = @user_id;
    
    IF @@ROWCOUNT = 0 BEGIN
		INSERT INTO users ([user_id], data) VALUES (@user_id, @data);
    END
    
    COMMIT;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_insert_or_update_user_gmail]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_insert_or_update_user_gmail]
	@user_gmail_id int,
	@data text
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
	BEGIN TRANSACTION;
	
    UPDATE user_gmail SET data = @data WHERE user_gmail_id = @user_gmail_id;
    
    IF @@ROWCOUNT = 0 BEGIN
		INSERT INTO user_gmail (user_gmail_id, data) VALUES (@user_gmail_id, @data);
    END
    
    COMMIT;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_write_channels_crc]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_write_channels_crc]
	-- Add the parameters for the stored procedure here
	@crc int
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	UPDATE parse_versions set channels_crc = @crc;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_write_user_gmail_crc]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_write_user_gmail_crc]
	-- Add the parameters for the stored procedure here
	@crc int
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	UPDATE parse_versions set user_gmail_crc = @crc;
END

GO
/****** Object:  StoredProcedure [dbo].[SP_write_users_crc]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[SP_write_users_crc]
	-- Add the parameters for the stored procedure here
	@crc int
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	UPDATE parse_versions set users_crc = @crc;
END

GO
/****** Object:  Table [dbo].[channels]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[channels](
	[name] [varchar](32) NOT NULL,
	[data] [text] NULL,
 CONSTRAINT [PK_channels] PRIMARY KEY CLUSTERED 
(
	[name] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

GO
SET ANSI_PADDING ON
GO
/****** Object:  Table [dbo].[parse_versions]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[parse_versions](
	[users_crc] [int] NULL,
	[channels_crc] [int] NULL,
	[user_gmail_crc] [int] NULL
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[user_gmail]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[user_gmail](
	[user_gmail_id] [int] NOT NULL,
	[data] [text] NULL,
 CONSTRAINT [PK_user_gmail] PRIMARY KEY CLUSTERED 
(
	[user_gmail_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

GO
/****** Object:  Table [dbo].[users]    Script Date: 4/19/2019 11:57:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[users](
	[user_id] [int] NOT NULL,
	[data] [text] NULL,
 CONSTRAINT [PK_users] PRIMARY KEY CLUSTERED 
(
	[user_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]
GO
INSERT [dbo].[parse_versions] ([users_crc], [channels_crc], [user_gmail_crc]) VALUES (0, 0, 0)

GO
USE [master]
GO
ALTER DATABASE [cohchat] SET  READ_WRITE 
GO
