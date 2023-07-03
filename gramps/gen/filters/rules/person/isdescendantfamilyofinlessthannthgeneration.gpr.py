"""Filter rule matching associations of <person filter>."""
register(
    RULE,
    id='IsDescendantFamilyOfInLessThanNthGeneration',
    name=_("Descendant family members of <person> not more than <N> generations away"),
    description=_("Matches people that are descendants or the spouse of a descendant of a specified person not more than N generations away"),
    version = '1.0.3',
    authors=["aq"],
    authors_email=["aq"],
    gramps_target_version='5.2',
    status=STABLE,
    fname="isdescendantfamilyofinlessthannthgeneration.py",
    ruleclass='IsDescendantFamilyOfInLessThanNthGeneration',
    namespace='Person',
    )