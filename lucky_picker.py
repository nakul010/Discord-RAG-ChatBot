import random

def pick_lucky_winner(range: str, count: int, seed : int, exclude: str):
    assert seed is not None
    assert count >= 1

    if not range.strip():
        return "Please provide a range.", None, None
    
    # Validate range
    range = range.split('-')
    if len(range) != 2:
        return "Please provide range in format `x-y`.", None, None
    if range[0] == range[1]:
        return "In range `x-y`, `x` and `y` cannot be the same.", None, None
    if not all(map(str.isdigit, range)):
        return "In range `x-y`, both `x` and `y` must be digits.", None, None
    range = [int(x) for x in range] # cast to int
    
    # Validate exclude
    if exclude.strip():
        exclude = exclude.split(',')
        exclude = list(map(str.strip, exclude)) # clean up whitespace
        exclude = [x for x in exclude if len(x) > 0] # drop empty string
        exclude = [x for x in exclude if x.isdigit()] # drop non-digits
        exclude = list(set(exclude)) # get unique
        exclude = [int(x) for x in exclude] # cast to int
    else:
        exclude = []
    
    start_range, end_range = min(range), max(range)

    # Validate count
    soft_limit = (end_range - start_range + 1) - len(exclude)
    count = min(soft_limit, count)
    if count > 100:  # Sanity limit
        return "Really? That's a really big range. I'm not doing it >:(", None, None

    # Logic to select lucky winners

    winners = []
    random.seed(seed)

    while len(winners) != count:
        candidate = random.randint(start_range, end_range)
        if candidate not in exclude and candidate not in winners:
            winners.append(candidate)

    winners.sort()
    winners = list(map(str, winners)) # cast to str
    return None, winners, seed

def get_random_seed() -> int:
    return random.randint(1, 500)
