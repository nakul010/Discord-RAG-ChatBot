import random


def pick_lucky_winner(range: str, count: int, seed: int, exclude: str):
    """Picks lucky number(s) from a given range

    Parameters:
        range (str): Range of numbers to choose from. Provided in `x-y` format. Both numbers are included as possible winners.
        count (int): Number of lucky winners. Should be more than 1.
        seed (int): Seed to initialse random. _Must not be `None`._
        exclude (str): Comma-seperated list of numbers to exclude from the winners. Format: `x1,x2,x3,...`

    Returns:
        tuple: A tuple containing three values:
            - error (str): Message of error faced.
            - winners (list): List of strings of the winning numbers.
            - seed_used (int): The seed used in the random picking.
        If error, then `winners` and `seed_used` would be `None`.
        Similarly, when `winners` and `seed_used`, then `error` would be `None`.
    """
    assert seed is not None

    if not range.strip():
        return "Please provide a range.", None, None

    # Validate range
    range = range.split("-")
    range = list(map(str.strip, range))  # clean up whitespace
    range = [x for x in range if len(x) > 0]  # drop empty string
    if len(range) != 2:
        return "Please provide range in format `x-y`.", None, None
    if range[0] == range[1]:
        return "In range `x-y`, `x` and `y` cannot be the same.", None, None
    if not all(map(str.isdigit, range)):
        return "In range `x-y`, both `x` and `y` must be digits.", None, None
    range = [int(x) for x in range]  # cast to int

    # Validate exclude
    if exclude.strip():
        exclude = exclude.split(",")
        exclude = list(map(str.strip, exclude))  # clean up whitespace
        exclude = [x for x in exclude if len(x) > 0]  # drop empty string
        exclude = [x for x in exclude if x.isdigit()]  # drop non-digits
        exclude = list(set(exclude))  # get unique
        exclude = [int(x) for x in exclude]  # cast to int
    else:
        exclude = []

    start_range, end_range = min(range), max(range)

    # Validate count
    soft_limit = (end_range - start_range + 1) - len(exclude)
    count = min(soft_limit, count)
    if count <= 0:
        return "There's no winner to pick.", None, None
    elif count > 100:  # Sanity limit
        return "Really? That's a really big range. I'm not doing it >:(", None, None

    # Logic to select lucky winners

    winners = []
    random.seed(seed)

    while len(winners) != count:
        candidate = random.randint(start_range, end_range)
        if candidate not in exclude and candidate not in winners:
            winners.append(candidate)

    winners.sort()
    winners = list(map(str, winners))  # cast to str
    return None, winners, seed


def get_random_seed() -> int:
    """Randomly generate a number between 1 and 500 to be used as a seed."""
    return random.randint(1, 500)
