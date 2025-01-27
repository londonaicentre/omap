-- rxnorm_ingredient_multiple_ingredients
select
  concept_id,
  concept_name,
  concept_code,
  vocabulary_id
from concept
where vocabulary_id = 'RxNorm'
and (concept_class_id = 'Ingredient' or concept_class_id = 'Multiple Ingredients')

-- rxnorm_clinical_drug
select
  concept_id,
  concept_name,
  concept_code,
  vocabulary_id
from concept
where vocabulary_id = 'RxNorm'
and concept_class_id = 'Clinical Drug'

-- dm+d_AMP / VMP / VTM
select
  concept_id,
  concept_name,
  concept_code,
  vocabulary_id
from concept
where vocabulary_id = 'dm+d'
and concept_class_id = 'AMP'
-- and concept_class_id = 'VMP'
-- and concept_class_id = 'VTM'

-- snomed_observable_entity
select
  concept_id,
  concept_name,
  concept_code,
  vocabulary_id
from concept
where vocabulary_id = 'SNOMED'
and (concept_class_id = 'Observable Entity')
