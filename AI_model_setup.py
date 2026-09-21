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


Gem38_flash = API_model('gemini-3.8-flash', "Gemini 3.8 Flash", 5, 20)
Gem37_flash = API_model('gemini-3.7-flash', "Gemini 3.7 Flash", 5, 20)
Gem31_flash_lite = API_model('gemini-3.1-flash-lite', 'Gemini 3.1 Flash Lite', 15, 500)
#Gem_pro = API_model('pro', 'Gemini Pro', 2, 50)

AI_models = [Gem38_flash, Gem37_flash, Gem31_flash_lite]
front_page_model = AI_models[0]