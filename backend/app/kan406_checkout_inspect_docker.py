import stripe, os
stripe.api_key = os.environ['STRIPE_SECRET_KEY']
for sid in ['cs_test_a1k0OLUyd0AjM8tBCBeTt1uJBO3N8r24IfNopHyDNmEGm7jIHzOeeNuPVV','cs_test_a13BGszPzfyvKsivthOQJYbNjjR3pFVcnzS5tUQNGZ7w2Sz4cGBUxfzHHf']:
    try:
        s = stripe.checkout.Session.retrieve(sid, expand=['line_items'])
        print(sid, s.get('amount_total'), s.get('currency'))
        for i in s.get('line_items',{}).get('data',[]):
            p = i.get('price', {})
            print('  ', p.get('id'), p.get('lookup_key'), i.get('amount_total'))
    except Exception as e:
        print(sid, 'ERR', e)
