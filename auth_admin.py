import discord


GIVE_DEV_PERMISSIONS = False  # Must be 'False' in production


valid_role_ids = [968790212140466206, 1062482414271737897]


def check_if_owner(intraction: discord.Interaction) -> bool:
    """
    Checks if the user of the interaction is 
    the owner of the guild which the interaction came from
    """
    return intraction.user == intraction.guild.owner


def check_admin_permission(user: discord.Member) -> bool:
    """
    Checks if user has Administrator permission
    
    The permission allows all permissions and bypasses channel permission overwrites.
    """
    return user.resolved_permissions.administrator


def check_has_role(user: discord.Member) -> bool:
    """Check if user has any of the white-listed valid roles"""
    return any(user_role.id in valid_role_ids for user_role in user.roles)


def check_has_permissions(interaction: discord.Interaction) -> bool:
    """Checks if user of interaction has privilege"""
    return check_if_owner(interaction) or\
        check_admin_permission(interaction.user) or\
        check_has_role(interaction.user) or\
        GIVE_DEV_PERMISSIONS
