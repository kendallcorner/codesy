from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings

import stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# codesy fee of 2.5% charged to offer and payout
codesy_pct = Decimal('0.025')

# stripe charge of 2.9% for credit card payments
stripe_pct = Decimal('0.029')

# stripe fee of 30 cents for each credit card payment
stripe_transaction = Decimal('0.30')

# stripe charge of 0.5% for transfering to bank account
stripe_transfer_pct = Decimal('0.005')


def round_penny(amount):
    return amount.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def calculate_codesy_fee(amount):
    return round_penny(amount * codesy_pct)


def calculate_stripe_fee(amount):
    return round_penny(
        (amount * (stripe_pct + stripe_transfer_pct)) + stripe_transaction
    )


def calculate_stripe_transfer(amount):
    return round_penny(amount * stripe_transfer_pct)


def calculate_charge_amount(goal):
    return round_penny(
        (goal + stripe_transaction) / (1 - stripe_pct)
    )


def calculate_offer_charge(goal):
    return round_penny(
        (goal + (stripe_transaction / 2))
        / (1 - ((stripe_pct + stripe_transfer_pct) / 2))
    )


def transaction_amounts(amount):
    codesy_fee_amount = calculate_codesy_fee(amount)

    charge_amount = calculate_offer_charge(
        amount
        + codesy_fee_amount
    )

    offer_stripe_fee = (
        charge_amount
        - amount
        - codesy_fee_amount
    )

    total_stripe_fee = calculate_stripe_fee(charge_amount)

    payout_stripe_fee = total_stripe_fee - offer_stripe_fee

    payout_amount = (
        amount
        - codesy_fee_amount
        - payout_stripe_fee
    )

    application_fee = (
        offer_stripe_fee
        + payout_stripe_fee
        + (codesy_fee_amount * 2)
    )

    gross_transfer_fee = calculate_stripe_transfer(amount)

    actual_transfer_fee = (
        calculate_stripe_transfer(payout_amount)
    )

    transfer_overage = (
        gross_transfer_fee
        - actual_transfer_fee
    )
    #This will never come to 0, since you are using 2 numbers to calculate the transfer fees that are supposed to be different (amount = payout_amount + payout_stripe_fee + codesy_fee_amount)to calculate it.

    charge_stripe_fee = charge_amount*stripe_pct +stripe_transaction

    return {
        'amount': amount,
        'charge_amount': round_penny(charge_amount),
        'payout_amount': payout_amount,
        'codesy_fee': codesy_fee_amount,
        'total_stripe_fee': total_stripe_fee,
        'offer_stripe_fee': offer_stripe_fee,
        'payout_stripe_fee': payout_stripe_fee,
        'application_fee': application_fee,
        'gross_transfer_fee': gross_transfer_fee,
        'actual_transfer_fee': actual_transfer_fee,
        'transfer_overage': transfer_overage,
        'charge_stripe_fee': charge_stripe_fee,
        'miscalculation_of_total_stripe_fee': (total_stripe_fee - charge_stripe_fee - actual_transfer_fee)
    }


def refund(offer):
    try:
        refund = stripe.Refund.create(
            charge=offer.charge_id
        )
        if refund:
            offer.refund_id = refund.id
    except Exception as e:
        print e.message
        offer.error_message = e.message
    offer.save()
    return offer.error_message == u''


def authorize(offer):
    try:
        # setting 'capture' to false makes this an Authorization request
        authorize = stripe.Charge.create(
            amount=int(offer.charge_amount * 100),
            currency="usd",
            customer=offer.bid.user.stripe_customer,
            description="Offer for: " + offer.bid.url,
            metadata={'bid_id': offer.bid.id},
            capture=False,
        )
        if authorize:
            offer.charge_id = authorize.id
            offer.api_success = True
        else:
            offer.error_message = "Authorization failed, please try later"
    except Exception as e:
        offer.error_message = e.message
    offer.save()


def charge(offer, payout):
    details = transaction_amounts(payout.amount)

    try:
        charge = stripe.Charge.create(
            customer=offer.user.stripe_customer,
            destination=payout.claim.user.account().account_id,
            amount=int(details['charge_amount'] * 100),
            currency="usd",
            description="Payout for: " + offer.bid.url,
            metadata={'bid_id': offer.bid.id},
            application_fee=int(details['application_fee'] * 100)
        )
        if charge:
            payout.charge_amount = details['payout_amount']
            payout.charge_id = charge.id
            payout.api_success = True
            payout.save()

            offer.api_success = True
            offer.charge_id = charge.id
            offer.save()

            payout.claim.status = 'Paid'
            payout.claim.save()
        else:
            offer.error_message = "Authorization failed, please try later"
    except Exception as e:
        print 'charge error: %s' % e.message
        offer.error_message = e.message
    offer.save()
