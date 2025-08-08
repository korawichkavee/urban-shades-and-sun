# urban-shades-and-sun


#TODO:Implement shadow/person localization on a per-image basis
ex: Are people in the shade or not in the shade?
    Just standing in the sun or moving away from the sun?
        Added classification (binary) -> use LLM?

#TODO: Expand dataset size -> Go beyond NUS 688 cities? (Why we care: Want more data) (Kieran)
How to do: look at NUS raw dowload code, create pipeline with lightweight annotation (specifically day)
Pipeline
    Raw download img manifests -> doesn't work (fully)
        Obtain metadata about images -> doesn't work 
            Compare datetime data against hot days

Literally just check for mapillary images taken on the hot day during download step. 

#TODO: Come up with better measure for "hot" (selected 35C arbitrarily, could note localized measures? (ex: person in Russia may be more sensitive to heat than a person in Indonesia))

#TODO: More specialized measure/filtering (ex: also add a filter from 10am-2pm so only when the sun is out)

#TODO: Get additional context about the environment around the image? -> 
    ex: mixed use streets? Is there shade in surrounding streets?

#TODO: Put a rough draft of stuf into intro section of overleaf (korawich to copy paste/repurpose stuff from other paper?)


#TODO: (potential option)
    Estimating the heat from the sun on individual people