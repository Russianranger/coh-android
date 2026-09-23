USE [master]
GO
/****** Object:  Database [cohauth]    Script Date: 4/19/2019 11:57:18 PM ******/
CREATE DATABASE [cohauth]
GO
ALTER DATABASE [cohauth] SET COMPATIBILITY_LEVEL = 100
GO
IF (1 = FULLTEXTSERVICEPROPERTY('IsFullTextInstalled'))
begin
EXEC [cohauth].[dbo].[sp_fulltext_database] @action = 'enable'
end
GO
ALTER DATABASE [cohauth] SET ANSI_NULL_DEFAULT OFF 
GO
ALTER DATABASE [cohauth] SET ANSI_NULLS ON 
GO
ALTER DATABASE [cohauth] SET ANSI_PADDING ON 
GO
ALTER DATABASE [cohauth] SET ANSI_WARNINGS OFF 
GO
ALTER DATABASE [cohauth] SET ARITHABORT OFF 
GO
ALTER DATABASE [cohauth] SET AUTO_CLOSE OFF 
GO
ALTER DATABASE [cohauth] SET AUTO_SHRINK OFF 
GO
ALTER DATABASE [cohauth] SET AUTO_UPDATE_STATISTICS ON 
GO
ALTER DATABASE [cohauth] SET CURSOR_CLOSE_ON_COMMIT OFF 
GO
ALTER DATABASE [cohauth] SET CURSOR_DEFAULT  GLOBAL 
GO
ALTER DATABASE [cohauth] SET CONCAT_NULL_YIELDS_NULL OFF 
GO
ALTER DATABASE [cohauth] SET NUMERIC_ROUNDABORT OFF 
GO
ALTER DATABASE [cohauth] SET QUOTED_IDENTIFIER OFF 
GO
ALTER DATABASE [cohauth] SET RECURSIVE_TRIGGERS OFF 
GO
ALTER DATABASE [cohauth] SET  DISABLE_BROKER 
GO
ALTER DATABASE [cohauth] SET AUTO_UPDATE_STATISTICS_ASYNC OFF 
GO
ALTER DATABASE [cohauth] SET DATE_CORRELATION_OPTIMIZATION OFF 
GO
ALTER DATABASE [cohauth] SET TRUSTWORTHY OFF 
GO
ALTER DATABASE [cohauth] SET ALLOW_SNAPSHOT_ISOLATION OFF 
GO
ALTER DATABASE [cohauth] SET PARAMETERIZATION SIMPLE 
GO
ALTER DATABASE [cohauth] SET READ_COMMITTED_SNAPSHOT OFF 
GO
ALTER DATABASE [cohauth] SET HONOR_BROKER_PRIORITY OFF 
GO
ALTER DATABASE [cohauth] SET RECOVERY FULL 
GO
ALTER DATABASE [cohauth] SET  MULTI_USER 
GO
ALTER DATABASE [cohauth] SET PAGE_VERIFY CHECKSUM  
GO
ALTER DATABASE [cohauth] SET DB_CHAINING OFF 
GO
EXEC sys.sp_db_vardecimal_storage_format N'cohauth', N'ON'
GO
USE [cohauth]
GO
/****** Object:  StoredProcedure [dbo].[ap_GPwd]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[ap_GPwd]
	-- Add the parameters for the stored procedure here
	@Name varchar(14),
	@Password binary(128) OUTPUT,
	@HashType int OUTPUT,
	@Salt int OUTPUT
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

    -- Insert statements for procedure here
	SELECT @Password = [password], @Salt = salt,
	@HashType = hash_type
	FROM user_auth with (nolock) WHERE account = @Name;
END

GO
/****** Object:  StoredProcedure [dbo].[ap_GStat]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[ap_GStat]
	-- Add the parameters for the stored procedure here
	@account varchar(14),
	@uid int OUTPUT,
	@pay_stat int OUTPUT,
	@login_flag int OUTPUT,
	@warn_flag int OUTPUT,
	@block_flag int OUTPUT,
	@block_flag2 int OUTPUT,
	@subscription_flag int OUTPUT,
	@lastworld tinyint OUTPUT,
	@block_end_date datetime2(3) OUTPUT,
	@queuelevel int OUTPUT,
	@loyalty int OUTPUT,
	@loyaltylegacy int OUTPUT
AS
BEGIN
	SET NOCOUNT ON;
	SELECT @uid = [uid],
	  @pay_stat = pay_stat,
	  @login_flag = login_flag,
	  @warn_flag = warn_flag,
	  @block_flag = block_flag,
	  @block_flag2 = block_flag2,
	  @subscription_flag = subscription_flag,
	  @lastworld = last_world,
	  @block_end_date = block_end_date,
	  @queuelevel = queue_level,
	  @loyalty = loyalty_points,
	  @loyaltylegacy = loyalty_legacy_points
	FROM user_account
	WHERE account = @account;
END

GO
/****** Object:  StoredProcedure [dbo].[ap_SLog]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[ap_SLog]
	-- Add the parameters for the stored procedure here
	@uid int,
	@login datetime,
	@logout datetime,
	@game_id int,
	@world_id int,
	@ip varchar(15)
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	UPDATE user_account SET
	    last_login = @login,
	    last_logout = @logout,
	    last_game = @game_id,
	    last_world = @world_id,
	    last_ip = @ip
	WHERE [uid] = @uid;
END

GO
/****** Object:  StoredProcedure [dbo].[get_server_groups]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[get_server_groups]
	-- Add the parameters for the stored procedure here
	@uid int
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

	SELECT server_group_id FROM user_server_group
	WHERE [uid] = @uid;
END

GO
/****** Object:  StoredProcedure [dbo].[sp_LogAuthActivity]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[sp_LogAuthActivity]
	-- Add the parameters for the stored procedure here
	@p1 varchar(14),
	@p2 int,
	@p3 int,
	@p4 varchar(15),
	@p5 datetime,
	@p6 datetime,
	@p7 datetime,
	@p8 datetime,
	@p9 varchar(255),
	@p10 int
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;
	-- Foo
END

GO
/****** Object:  StoredProcedure [dbo].[sp_LogUserNumbers]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
-- =============================================
-- Author:		<Author,,Name>
-- Create date: <Create Date,,>
-- Description:	<Description,,>
-- =============================================
CREATE PROCEDURE [dbo].[sp_LogUserNumbers]
	@record_time datetime,
	@server_id int,
	@world_user int,
	@limit_user int,
	@auth_user int,
    @wait_user int
AS
BEGIN
	-- SET NOCOUNT ON added to prevent extra result sets from
	-- interfering with SELECT statements.
	SET NOCOUNT ON;

/*INSERT INTO user_count
(
	record_time,
	server_id,
	world_user,
	limit_user,
	auth_user,
	wait_user
)
VALUES
(
	@record_time,
	@server_id,
	@world_user,
	@limit_user,
	@auth_user,
	@wait_user
) */
END

GO
/****** Object:  Table [dbo].[block_msg]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[block_msg](
	[uid] [int] NOT NULL,
	[reason] [int] NOT NULL,
	[msg] [varchar](255) NULL,
 CONSTRAINT [PK_block_msg] PRIMARY KEY CLUSTERED 
(
	[uid] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING ON
GO
/****** Object:  Table [dbo].[gm_illegal_login]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[gm_illegal_login](
	[account] [varchar](32) NULL,
	[ip] [varchar](16) NULL
) ON [PRIMARY]

GO
SET ANSI_PADDING ON
GO
/****** Object:  Table [dbo].[server]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[server](
	[id] [int] NOT NULL,
	[name] [varchar](max) NULL,
	[ip] [varchar](256) NULL,
	[inner_ip] [varchar](256) NULL,
	[ageLimit] [int] NULL,
	[pk_flag] [int] NULL,
	[server_group_id] [int] NULL,
	[client_port] [smallint] NULL,
 CONSTRAINT [PK_server] PRIMARY KEY CLUSTERED 
(
	[id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

GO
SET ANSI_PADDING ON
GO
/****** Object:  Table [dbo].[user_account]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[user_account](
	[account] [varchar](14) NOT NULL,
	[uid] [int] NULL,
	[pay_stat] [int] NOT NULL,
	[login_flag] [int] NOT NULL,
	[warn_flag] [int] NOT NULL,
	[block_flag] [int] NOT NULL,
	[block_flag2] [int] NOT NULL,
	[last_login] [datetime] NULL,
	[last_logout] [datetime] NULL,
	[subscription_flag] [int] NOT NULL,
	[last_world] [tinyint] NULL,
	[last_game] [int] NULL,
	[last_ip] [varchar](15) NULL,
	[block_end_date] [datetime] NULL,
	[queue_level] [int] NOT NULL,
	[product_id] [int] NULL,
	[loyalty_points] [int] NULL,
	[loyalty_legacy_points] [int] NULL,
	[forum_id] [int] NULL,
 CONSTRAINT [PK_user_account] PRIMARY KEY CLUSTERED 
(
	[account] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING ON
GO
/****** Object:  Table [dbo].[user_auth]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[user_auth](
	[account] [varchar](14) NOT NULL,
	[password] [binary](128) NOT NULL,
	[salt] [int] NOT NULL,
	[hash_type] [tinyint] NOT NULL,
 CONSTRAINT [PK_user_auth] PRIMARY KEY CLUSTERED 
(
	[account] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING ON
GO
/****** Object:  Table [dbo].[user_count]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[user_count](
	[record_time] [datetime] NOT NULL,
	[server_id] [tinyint] NOT NULL,
	[world_user] [int] NOT NULL,
	[limit_user] [int] NOT NULL,
	[auth_user] [int] NOT NULL,
	[wait_user] [int] NOT NULL,
	[dayofweek] [tinyint] NOT NULL,
	[product_id] [int] NULL
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[user_data]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[user_data](
	[uid] [int] NOT NULL,
	[user_data] [binary](16) NULL,
	[user_data_new] [binary](112) NULL,
	[user_game_data] [binary](16) NOT NULL,
	[user_game_data_new] [binary](112) NOT NULL,
 CONSTRAINT [PK_user_data] PRIMARY KEY CLUSTERED 
(
	[uid] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING ON
GO
/****** Object:  Table [dbo].[user_info]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
SET ANSI_PADDING ON
GO
CREATE TABLE [dbo].[user_info](
	[account] [varchar](14) NOT NULL,
	[ssn] [varchar](11) NULL,
 CONSTRAINT [PK_user_info] PRIMARY KEY CLUSTERED 
(
	[account] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
SET ANSI_PADDING ON
GO
/****** Object:  Table [dbo].[user_server_group]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[user_server_group](
	[uid] [int] NOT NULL,
	[server_group_id] [int] NOT NULL,
 CONSTRAINT [PK_user_server_groups] PRIMARY KEY CLUSTERED 
(
	[uid] ASC,
	[server_group_id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Table [dbo].[worldstatus]    Script Date: 4/19/2019 11:57:18 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[worldstatus](
	[idx] [int] NOT NULL,
	[status] [int] NULL,
 CONSTRAINT [PK_worldstatus] PRIMARY KEY CLUSTERED 
(
	[idx] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
) ON [PRIMARY]

GO
/****** Object:  Index [IX_user_account]    Script Date: 4/19/2019 11:57:18 PM ******/
CREATE NONCLUSTERED INDEX [IX_user_account] ON [dbo].[user_account]
(
	[uid] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON) ON [PRIMARY]
GO
ALTER TABLE [dbo].[block_msg] ADD  CONSTRAINT [DF_block_msg_reason]  DEFAULT ((0)) FOR [reason]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p3]  DEFAULT ((0)) FOR [pay_stat]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p4]  DEFAULT ((0)) FOR [login_flag]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p5]  DEFAULT ((0)) FOR [warn_flag]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p6]  DEFAULT ((0)) FOR [block_flag]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p7]  DEFAULT ((0)) FOR [block_flag2]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p8]  DEFAULT ((0)) FOR [subscription_flag]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p9]  DEFAULT ((0)) FOR [last_world]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p11]  DEFAULT ((0)) FOR [queue_level]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p12]  DEFAULT ((0)) FOR [loyalty_points]
GO
ALTER TABLE [dbo].[user_account] ADD  CONSTRAINT [DF_user_account_p13]  DEFAULT ((0)) FOR [loyalty_legacy_points]
GO
ALTER TABLE [dbo].[user_auth] ADD  CONSTRAINT [DF_user_auth_salt]  DEFAULT ((0)) FOR [salt]
GO
ALTER TABLE [dbo].[user_auth] ADD  CONSTRAINT [DF_user_auth_hash_type]  DEFAULT ((0)) FOR [hash_type]
GO
ALTER TABLE [dbo].[user_count] ADD  CONSTRAINT [DF_user_count_record_time]  DEFAULT (getdate()) FOR [record_time]
GO
ALTER TABLE [dbo].[user_count] ADD  CONSTRAINT [DF_user_count_dayofweek]  DEFAULT (datepart(weekday,getdate())) FOR [dayofweek]
GO
ALTER TABLE [dbo].[user_data] ADD  CONSTRAINT [DF_user_data_user_data]  DEFAULT (0x00) FOR [user_data]
GO
ALTER TABLE [dbo].[user_data] ADD  CONSTRAINT [DF_user_data_user_data_new_1]  DEFAULT (0x00) FOR [user_data_new]
GO
ALTER TABLE [dbo].[user_data] ADD  CONSTRAINT [DF_user_data_user_game_data]  DEFAULT (0x00) FOR [user_game_data]
GO
ALTER TABLE [dbo].[user_data] ADD  CONSTRAINT [DF_user_data_user_game_data_new]  DEFAULT (0x00) FOR [user_game_data_new]
GO
USE [master]
GO
ALTER DATABASE [cohauth] SET  READ_WRITE 
GO
