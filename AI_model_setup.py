class API_model():

    def __init__(self, id, name, RPM, RPD):
        self.id = id
        self.name = name
        self.n_calls = 0
        self.is_exhausted = False
        self.in_high_demand = False
        self.RPM = RPM
        self.sleeptime = 60 // self.RPM
        self.rate_limit = RPD

    def rate_limit_reached(self):
        if self.n_calls > self.rate_limit:
            self.is_exhausted = True
            return True
        else:
            return False


Gem25_flash = API_model('gemini-2.5-flash', 'Gemini Flash', 5, 20)
Gem3_flash = API_model('gemini-3-flash-preview', 'Gemini 3 Flash', 5, 20)
Gem35_flash = API_model('gemini-3.5-flash', "Gemini 3.5 Flash", 5, 20)
Gem31_flash_lite = API_model('gemini-3.1-flash-lite', 'Gemini 3.1 Flash Lite', 15, 500)
#Gem_pro = API_model('pro', 'Gemini Pro', 2, 50)

AI_models = [Gem35_flash, Gem3_flash, Gem31_flash_lite, Gem25_flash]
front_page_model = Gem35_flash