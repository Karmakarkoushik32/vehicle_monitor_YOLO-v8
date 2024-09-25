def formatTime(time_in_Sec):
    hours, remainder = divmod(time_in_Sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    # Formatting the time delta as HH:MM:SS
    return  f"{hours:02}:{minutes:02}:{seconds:.2f}"