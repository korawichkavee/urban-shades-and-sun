# urban-shades-and-sun


#TODO:Implement shadow/person localization on a per-image basis
ex: Are people in the shade or not in the shade?
    Just standing in the sun or moving away from the sun?
        Added classification (binary) -> use LLM?
            Goals:
                Num people in img
                    Num people in the shade (potentially w/masking)
                        vs num people in the sun
                Side goal: are they moving or not?

#TODO: Expand dataset size -> Go beyond NUS 688 cities? (Why we care: Want more data) (Kieran)
How to do: look at NUS raw dowload code, create pipeline with lightweight annotation (specifically day)
Pipeline
    Raw download img manifests -> doesn't work (fully)
        Obtain metadata about images -> doesn't work 
            Compare datetime data against hot days
                Could filter by pop in city? (ex: pop below 200k, exclude)
    Check results for num images from some cities against NUS dataset?
    Potential issue: global streetscapes spatial sampling is close to city center rather than across entire city
        Method to change?

Literally just check for mapillary images taken on the hot day during download step. 

#TODO: Come up with better measure for "hot" (selected 30C arbitrarily, could note localized measures? (ex: person in Russia may be more sensitive to heat than a person in Indonesia)) -> Lit review ish task

#TODO: More specialized measure/filtering? (ex: also add a filter from 10am-2pm so only when the sun is out)

#TODO: Get additional context about the environment around the image? -> 
    ex: mixed use streets? Is there shade in surrounding streets?

#TODO: Put a rough draft of stuf into intro section of overleaf (korawich to copy paste/repurpose stuff from other paper?)

#TODO: How can we/can we? account for potential sampling bias (ex: people less likely to take mapillary images on very hot days)
    Filip paper?
    Do temp analysis of NUS dataset? 


#TODO: (potential option)
    Estimating the heat from the sun on individual people


#TODO: Control example (imgs from regular temp days)


#TODO:Scale size of shadow boundary by size of person (num pixels)

#TODO: Compute shadow angle as defense for stuff?

#TODO: 10 cities per continent as a test?

