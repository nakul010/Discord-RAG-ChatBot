import discord

GIVE_DEV_PERMISSIONS = False  # Must be 'False' in production

valid_role_ids = [968790212140466206, 1062482414271737897]

def check_has_role(user: discord.Member) -> bool:
    return GIVE_DEV_PERMISSIONS or\
        any(user_role.id in valid_role_ids for user_role in user.roles)
