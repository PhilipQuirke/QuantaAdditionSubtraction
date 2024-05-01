from QuantaTools.useful_node import position_name, answer_name, UsefulNode, UsefulNodeList

from QuantaTools.quanta_constants import QType, QCondition, NO_IMPACT_TAG
from QuantaTools.quanta_map_impact import sort_unique_digits
from QuantaTools.quanta_filter import FilterNode, FilterAnd, FilterOr, FilterHead, \
     FilterContains, FilterPosition, FilterAttention, FilterImpact, FilterAlgo

from QuantaTools.ablate_config import AblateConfig

from .maths_constants import MathsToken, MathsBehavior, MathsTask 
from .maths_search_mix import succeed_test, math_common_prereqs, \
    run_strong_intervention, run_weak_intervention



# Tag for positive-answer subtraction "Difference" (MD) tasks e.g. 666666-222222=+0444444 where D3 >= D'3
def sub_md_tag(impact_digit):
    return answer_name(impact_digit) + "." + MathsTask.MD_TAG.value


# Prerequisites for positive-answer subtraction "Difference" (MD) tasks 
def sub_md_prereqs(cfg, position, impact_digit):
    # Pays attention to Dn and D'n. Impacts An
    return math_common_prereqs(cfg, position, impact_digit, impact_digit)


def sub_md_test1(cfg, alter_digit):
    # 333333 - 111111 = +222222. No Dn.MB
    store_question = [cfg.repeat_digit(3), cfg.repeat_digit(1)]

    # 999999 - 444444 = +555555. No DN.MB
    clean_question = [cfg.repeat_digit(9), cfg.repeat_digit(4)]

    # When we intervene we expect answer +555255
    intervened_answer = clean_question[0] - clean_question[1] + (2-5) * 10 ** alter_digit

    return store_question, clean_question, intervened_answer


def sub_md_test2(cfg, alter_digit):
    # 666666 - 222222 = +444444. No DN.MB
    store_question = [cfg.repeat_digit(6), cfg.repeat_digit(2)]

    # 999999 - 333333 = +666666. No DN.MB
    clean_question = [cfg.repeat_digit(9), cfg.repeat_digit(3)]

    # When we intervene we expect answer +666466
    intervened_answer = clean_question[0] - clean_question[1] + (4-6) * 10 ** alter_digit

    return store_question, clean_question, intervened_answer


# Intervention ablation test for positive-answer subtraction "Difference" (MD) tasks 
def sub_md_test(cfg, acfg, alter_digit, strong):
    # Note: MD and SA give the same result when D'=0 or D=D'=5. We avoid ablation tests like this.
    
    intervention_impact = answer_name(alter_digit)

    store_question, clean_question, intervened_answer = sub_md_test1(cfg, alter_digit)
    success1, _, impact_success1 = run_strong_intervention(cfg, acfg, store_question, clean_question, intervention_impact, intervened_answer)

    store_question, clean_question, intervened_answer = sub_md_test2(cfg, alter_digit)
    success2, _, impact_success2 = run_strong_intervention(cfg, acfg, store_question, clean_question, intervention_impact, intervened_answer)

    success = (success1 and success2) if strong else (impact_success1 and impact_success2)

    if success:
        print( "Test confirmed", acfg.ablate_node_names(), "perform A"+str(alter_digit)+".MD = (D"+str(alter_digit)+" + D'"+str(alter_digit)+") % 10 impacting "+intervention_impact+" accuracy.", "" if strong else "Weak")

    return success


# Tag for positive-answer subtraction "Borrow One" (MB) task e.g. 222222-111311=+0110911 where D2 > D'2
def sub_mb_tag(impact_digit):
    return answer_name(impact_digit-1)  + "." + MathsTask.MB_TAG.value    


# Prerequisites for positive-answer subtraction "Borrow One" (MB) task
def sub_mb_prereqs(cfg, position, impact_digit):
    # Pays attention to Dn-1 and D'n-1. Impacts An    
    return math_common_prereqs(cfg,  position, impact_digit-1, impact_digit)


# Intervention ablation test for positive-answer subtraction "Borrow One" (MB) task
def sub_mb_test(cfg, acfg, impact_digit, strong):
    alter_digit = impact_digit - 1

    if alter_digit < 0 or alter_digit >= cfg.n_digits:
        acfg.reset_intervention()
        return False

    intervention_impact = answer_name(impact_digit)

    # 222222 - 111311 = +0110911. Has Dn.MB
    store_question = [cfg.repeat_digit(2), cfg.repeat_digit(1)]
    store_question[1] += (3 - 1) * (10 ** alter_digit)

    # 777777 - 444444 = +0333333. No Dn.MB
    clean_question = [cfg.repeat_digit(7), cfg.repeat_digit(4)]

    # When we intervene we expect answer +0332333
    intervened_answer = clean_question[0] - clean_question[1] - 10 ** (alter_digit+1)

    success, _, _ = run_strong_intervention(cfg, acfg, store_question, clean_question, intervention_impact, intervened_answer)

    if success:
        print( "Test confirmed", acfg.ablate_node_names(), "perform A"+str(alter_digit)+".MB impacting "+intervention_impact+" accuracy.", "" if strong else "Weak")
        
    return success


# Tag for positive-answer subtraction "TriCase" task "MT"
def sub_mt_tag(impact_digit):
    return answer_name(impact_digit)  + "." + MathsTask.MT_TAG.value


def sub_mt_prereqs(cfg, position, focus_digit):
    return FilterAnd(
        FilterHead(),
        FilterPosition(position_name(cfg.n_digits), QCondition.MIN), # Occurs in early tokens
        FilterPosition(position_name(cfg.num_question_positions), QCondition.MAX), # Occurs in early tokens   
        FilterAttention(cfg.dn_to_position_name(focus_digit)), # Attends to Dn
        FilterAttention(cfg.ddn_to_position_name(focus_digit)), # Attends to D'n
        FilterContains(QType.MATH_SUB, MathsBehavior.SUB_PCA_TAG.value), # Node PCA is interpretable (bigram or trigram output) with respect to subtraction T8,T9,T10
        FilterContains(QType.MATH_SUB, MathsBehavior.SUB_COMPLEXITY_PREFIX.value), # Impacts positive-answer questions (cover M1 to M4)
        FilterPosition(position_name(position)))


# Test that if we ablate this node then a negative-answer-subtraction question answer swaps to its positive complement
def sub_mt_test(cfg, acfg, focus_digit, strong):

    if focus_digit >= cfg.n_digits:
        acfg.reset_intervention()
        return False

    # 555555 - 000000 = +0555555. Is a positive-answer-subtraction
    store_question = [cfg.repeat_digit(5), cfg.repeat_digit(0)]

    # 222222 - 222422 = -0000200. Is a negative-answer-subtraction question because of focus_digit
    clean_question = [cfg.repeat_digit(2), cfg.repeat_digit(2)]
    clean_question[1] += 2 * (10 ** focus_digit)

    success = run_weak_intervention(cfg, acfg, store_question, clean_question)

    if success:
        print("Test confirmed", acfg.ablate_node_names(), " perform D"+str(focus_digit)+".MT", "Impact:", acfg.intervened_impact, "" if strong else "Weak")

    return success


# Negative-answer subtraction "Difference" (ND) task tag
def neg_nd_tag(impact_digit):
    return answer_name(impact_digit) + "." + MathsTask.ND_TAG.value


# These rules are prerequisites for (not proof of) a Neg Difference node
def neg_nd_prereqs(cfg, position, impact_digit):
    # Impacts An and pays attention to Dn and D'n
    return math_common_prereqs(cfg, position, impact_digit, impact_digit)


def neg_nd_test1(cfg, acfg, alter_digit):
    # 033333 - 111111 = -077778. No Dn.NB
    store_question = [cfg.repeat_digit(3), cfg.repeat_digit(1)]
    store_question[0] = store_question[0] // 10 # Convert 333333 to 033333

    # 099999 - 444444 = -344445. No Dn.NB
    clean_question = [cfg.repeat_digit(9), cfg.repeat_digit(4)]
    clean_question[0] = clean_question[0] // 10 # Convert 999999 to 099999

    # When we intervene we expect answer -347445
    intervened_answer = clean_question[0] - clean_question[1] - (7-4) * 10 ** alter_digit

    # Unit test
    if cfg.n_digits == 6 and alter_digit == 3:
        assert store_question[0] == 33333
        assert clean_question[0] == 99999
        assert clean_question[0] - clean_question[1] == -344445
        assert intervened_answer == -347445

    return store_question, clean_question, intervened_answer


def neg_nd_test2(cfg, acfg, alter_digit):
    # 066666 - 222222 = -155556. No Dn.NB
    store_question = [cfg.repeat_digit(6), cfg.repeat_digit(2)]
    store_question[0] = store_question[0] // 10 # Remove top digit

    # 099999 - 333333 = -233334. No Dn.NB
    clean_question = [cfg.repeat_digit(9), cfg.repeat_digit(3)]
    clean_question[0] = clean_question[0] // 10 # Remove top digit

    # When we intervene we expect answer -231334
    intervened_answer = clean_question[0] - clean_question[1] - (5-3) * 10 ** alter_digit

    return store_question, clean_question, intervened_answer


# Negative-answer subtraction "Difference" (ND) task ablation test
def neg_nd_test(cfg, acfg, alter_digit, strong):
    intervention_impact = answer_name(alter_digit)

    store_question, clean_question, intervened_answer = neg_nd_test1(cfg, acfg, alter_digit)
    success1, _, impact_success1 = run_strong_intervention(cfg, acfg, store_question, clean_question, intervention_impact, intervened_answer)

    store_question, clean_question, intervened_answer = neg_nd_test2(cfg, acfg, alter_digit)
    success2, _, impact_success2 = run_strong_intervention(cfg, acfg, store_question, clean_question, intervention_impact, intervened_answer)

    success = (success1 and success2) if strong else (impact_success1 and impact_success2)

    if success:
        print( "Test confirmed", acfg.ablate_node_names(), "perform A"+str(alter_digit)+".ND = (D"+str(alter_digit)+" + D'"+str(alter_digit)+") % 10 impacting "+intervention_impact+" accuracy.", "" if strong else "Weak")

    return success


# Negative-answer subtraction "Borrow One" (NB) task tag
def neg_nb_tag(impact_digit):
    return answer_name(impact_digit) + "." + MathsTask.NB_TAG.value


# Prerequisites for negative-answer subtraction "Borrow One" (NB) task
def neg_nb_prereqs(cfg, position, impact_digit):
    # Pays attention to Dn-1 and D'n-1. Impacts An
    return math_common_prereqs(cfg,  position, impact_digit-1, impact_digit)


# Intervention ablation test for negative-answer subtraction "Borrow One" (NB) task
def neg_nb_test(cfg, acfg, impact_digit, strong):
    alter_digit = impact_digit - 1

    if alter_digit < 0 or alter_digit >= cfg.n_digits:
        acfg.reset_intervention()
        return False

    intervention_impact = answer_name(impact_digit)

    # 022222 - 111311 = -0089089. Has Dn.MB
    store_question = [cfg.repeat_digit(2), cfg.repeat_digit(1)]
    store_question[0] = store_question[0] // 10 # Convert 222222 to 022222
    store_question[1] += (3 - 1) * (10 ** alter_digit)

    # 077777 - 444444 = -0366667. No Dn.MB
    clean_question = [cfg.repeat_digit(7), cfg.repeat_digit(4)]
    clean_question[0] = clean_question[0] // 10 # Convert 777777 to 077777

    # When we intervene we expect answer -0366677
    intervened_answer = clean_question[0] - clean_question[1] - 10 ** (alter_digit+1)

    success, _, _ = run_strong_intervention(cfg, acfg, store_question, clean_question, intervention_impact, intervened_answer)

    if success:
        print( "Test confirmed", acfg.ablate_node_names(), "perform A"+str(alter_digit)+".NB impacting "+intervention_impact+" accuracy.", "" if strong else "Weak")

    return success