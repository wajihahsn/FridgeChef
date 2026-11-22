"""Build data/sample_recipes.json (hand-written offline starter set, ~110 recipes).
Format per line:  name | minutes | ingredient, ingredient, ... | step; step; step
Usage: python scripts/build_sample_data.py"""
import json
import os

RAW = """
Tomato Omelette | 10 | eggs, tomato, onion, salt, butter | Saute chopped onion and tomato in butter; Pour in beaten eggs and cook until set
Spinach Cheese Omelette | 10 | eggs, spinach, cheese, butter | Wilt spinach in butter; Add beaten eggs and cheese, fold and serve
Mushroom Omelette | 12 | eggs, mushroom, butter, cheese, salt | Brown sliced mushrooms in butter; Add beaten eggs and cheese and fold
Scrambled Eggs on Toast | 8 | eggs, bread, butter, milk, salt | Whisk eggs with milk; Scramble gently in butter; Serve on toasted bread
Egg Fried Rice | 15 | rice, eggs, carrot, onion, soy sauce, oil | Stir fry onion and carrot; Add cooked rice, eggs and soy sauce; Toss until hot
Vegetable Fried Rice | 18 | rice, carrot, pea, onion, soy sauce, garlic, oil | Fry garlic and onion; Add vegetables and rice; Season with soy sauce
Tomato Pasta | 20 | pasta, tomato, garlic, onion, olive oil, cheese | Boil pasta; Cook garlic, onion and tomato into a sauce; Toss with pasta and cheese
Creamy Mushroom Pasta | 25 | pasta, mushroom, cream, garlic, butter | Boil pasta; Cook mushrooms and garlic in butter; Stir in cream and toss with pasta
Garlic Butter Pasta | 15 | pasta, garlic, butter, parsley, cheese | Boil pasta; Melt garlic in butter; Toss with parsley and cheese
Pasta Carbonara | 25 | pasta, eggs, bacon, cheese, pepper | Boil pasta; Crisp the bacon; Toss hot pasta with eggs and cheese off the heat
Chicken Rice Bowl | 35 | chicken, rice, onion, garlic, soy sauce, oil | Brown chicken with onion and garlic; Add soy sauce; Serve over rice
Lemon Garlic Chicken | 30 | chicken, lemon, garlic, butter, salt | Sear chicken in butter; Add garlic and lemon juice; Simmer until cooked
Chicken Curry | 45 | chicken, onion, tomato, garlic, ginger, yogurt, chili powder, oil | Fry onion, garlic and ginger; Add tomato, spices and chicken; Simmer with yogurt
Chicken Noodle Soup | 40 | chicken, noodles, carrot, celery, onion, water | Simmer chicken with vegetables; Add noodles; Shred chicken and serve
Chicken Fajitas | 25 | chicken, bell pepper, onion, tortilla, cumin, lime | Slice chicken and vegetables; Fry with cumin; Serve in tortillas with lime
Chicken Salad Sandwich | 15 | chicken, bread, mayonnaise, celery, lettuce | Mix shredded chicken with mayonnaise and celery; Layer on bread with lettuce
Chicken Stir Fry | 20 | chicken, broccoli, carrot, garlic, soy sauce, oil | Stir fry chicken; Add vegetables and garlic; Finish with soy sauce
Creamy Potato Mash | 30 | potato, milk, butter, salt | Boil potatoes; Mash with warm milk and butter
Cheesy Baked Potato | 55 | potato, cheese, onion, butter, sour cream | Bake potatoes; Split and top with cheese, onion and sour cream
Potato Wedges | 40 | potato, olive oil, paprika, garlic, salt | Cut potatoes into wedges; Toss with oil and spices; Roast until golden
Potato Soup | 35 | potato, onion, milk, butter, garlic | Soften onion in butter; Simmer with potato; Blend and stir in milk
Aloo Gobi | 40 | potato, cauliflower, onion, tomato, cumin, ginger, oil | Fry onion and spices; Add vegetables and tomato; Cover and cook until soft
Spanish Tortilla | 35 | potato, eggs, onion, olive oil, salt | Fry sliced potato and onion; Mix with eggs; Cook as a thick omelette
Beef Burger | 25 | beef, bread, onion, lettuce, tomato, cheese | Shape and grill patties; Serve in bread with toppings
Beef Tacos | 25 | beef, tortilla, tomato, onion, cheese, cumin, lettuce | Brown beef with cumin; Fill tortillas and add toppings
Spaghetti Bolognese | 50 | beef, pasta, tomato, onion, garlic, carrot, olive oil | Brown beef with onion and garlic; Simmer with tomato and carrot; Serve over pasta
Beef Stir Fry | 20 | beef, bell pepper, onion, soy sauce, garlic, oil | Sear beef; Add vegetables and garlic; Finish with soy sauce
Beef and Potato Stew | 90 | beef, potato, carrot, onion, tomato paste, water | Brown beef; Add vegetables and tomato paste; Simmer until tender
Chili Con Carne | 60 | beef, kidney bean, tomato, onion, garlic, chili powder, cumin | Brown beef and onion; Add beans, tomato and spices; Simmer
Shepherd's Pie | 70 | beef, potato, carrot, onion, pea, butter, milk | Cook beef with vegetables; Top with mashed potato; Bake until golden
Grilled Cheese Sandwich | 10 | bread, cheese, butter | Butter the bread; Fill with cheese; Fry until golden
Cheese Toast | 8 | bread, cheese, butter | Top bread with cheese; Grill until melted
French Toast | 15 | bread, eggs, milk, sugar, butter | Whisk eggs, milk and sugar; Soak bread; Fry in butter
Avocado Toast | 8 | bread, avocado, lemon, salt, tomato | Toast the bread; Mash avocado with lemon; Top with tomato
Egg Sandwich | 12 | bread, eggs, mayonnaise, lettuce, salt | Boil and chop eggs; Mix with mayonnaise; Fill bread with lettuce
Tuna Sandwich | 10 | tuna, bread, mayonnaise, celery, lettuce | Mix tuna with mayonnaise and celery; Fill bread
Tuna Pasta | 20 | tuna, pasta, tomato, garlic, olive oil, parsley | Boil pasta; Warm garlic and tomato; Toss with tuna and parsley
Tuna Salad | 10 | tuna, lettuce, tomato, cucumber, olive oil, lemon | Combine vegetables and tuna; Dress with oil and lemon
Greek Salad | 10 | cucumber, tomato, onion, feta, olive oil, olive | Chop vegetables; Add feta and olives; Dress with oil
Caprese Salad | 8 | tomato, mozzarella, basil, olive oil, salt | Slice tomato and mozzarella; Layer with basil and drizzle oil
Cucumber Yogurt Salad | 8 | cucumber, yogurt, garlic, mint, salt | Grate cucumber; Mix with yogurt, garlic and mint
Green Salad | 8 | lettuce, cucumber, tomato, carrot, olive oil, lemon | Chop vegetables; Dress with oil and lemon
Coleslaw | 12 | cabbage, carrot, mayonnaise, vinegar, sugar | Shred vegetables; Mix with mayonnaise, vinegar and sugar
Potato Salad | 30 | potato, eggs, mayonnaise, onion, celery, salt | Boil potatoes and eggs; Chop and fold with mayonnaise and onion
Pasta Salad | 20 | pasta, tomato, cucumber, olive, olive oil, cheese | Boil and cool pasta; Toss with vegetables and oil
Chickpea Salad | 10 | chickpea, cucumber, tomato, onion, lemon, olive oil | Mix everything; Dress with lemon and oil
Hummus | 10 | chickpea, garlic, lemon, tahini, olive oil, salt | Blend chickpeas, tahini, garlic and lemon; Drizzle with oil
Chana Masala | 35 | chickpea, onion, tomato, garlic, ginger, chili powder, cumin, oil | Fry onion, garlic and ginger; Add tomato and spices; Simmer chickpeas
Lentil Soup | 40 | lentil, onion, carrot, garlic, cumin, water | Fry onion and carrot; Add lentils, cumin and water; Simmer until soft
Dal Tadka | 35 | lentil, onion, tomato, garlic, cumin, butter | Boil lentils; Fry onion, garlic and cumin in butter; Mix together
Black Bean Burritos | 20 | black bean, rice, tortilla, cheese, onion, cumin | Warm beans with cumin; Fill tortillas with rice and cheese
Bean Quesadilla | 15 | kidney bean, tortilla, cheese, onion, cumin | Mash beans with cumin; Fill tortilla with cheese; Fry until crisp
Cheese Quesadilla | 10 | tortilla, cheese, butter | Fill tortilla with cheese; Fry in butter until crisp
Veggie Quesadilla | 15 | tortilla, cheese, bell pepper, onion, mushroom | Saute vegetables; Fill tortilla with cheese; Fry until crisp
Mushroom Risotto | 40 | rice, mushroom, onion, butter, cheese, garlic, water | Soften onion and garlic; Stir in rice and warm water gradually; Finish with butter and cheese
Rice Pudding | 40 | rice, milk, sugar, cinnamon, butter | Simmer rice in milk; Sweeten and add cinnamon
Egg Curry | 30 | eggs, onion, tomato, garlic, ginger, chili powder, oil | Boil eggs; Make a sauce with onion, tomato and spices; Simmer eggs
Shakshuka | 25 | eggs, tomato, bell pepper, onion, garlic, cumin, olive oil | Cook vegetables with cumin; Make wells and poach eggs in the sauce
Egg Salad | 15 | eggs, mayonnaise, mustard, celery, salt | Boil and chop eggs; Mix with mayonnaise and mustard
Deviled Eggs | 20 | eggs, mayonnaise, mustard, paprika, salt | Halve boiled eggs; Mix yolks with mayonnaise and mustard; Refill and dust with paprika
Veggie Omelette | 12 | eggs, bell pepper, onion, tomato, cheese, butter | Saute vegetables; Add eggs and cheese; Fold
Pancakes | 20 | flour, milk, eggs, sugar, butter, baking powder | Whisk batter; Fry spoonfuls in butter until golden
Banana Pancakes | 15 | banana, eggs, flour, milk, butter | Mash banana into batter; Fry small pancakes
Banana Smoothie | 5 | banana, milk, honey, yogurt | Blend everything until smooth
Berry Yogurt Bowl | 5 | yogurt, strawberry, honey, oat | Layer yogurt, berries and oats; Drizzle honey
Oatmeal with Banana | 10 | oat, milk, banana, honey, cinnamon | Simmer oats in milk; Top with banana and honey
Apple Crumble | 50 | apple, flour, butter, sugar, oat, cinnamon | Slice apples; Rub butter into flour, sugar and oats; Bake until golden
Banana Bread | 60 | banana, flour, eggs, sugar, butter, baking soda | Mash bananas; Mix with batter; Bake until set
Fruit Salad | 10 | apple, banana, orange, grape, honey | Chop fruit; Toss with honey
Guacamole | 10 | avocado, tomato, onion, lime, cilantro, salt | Mash avocado; Mix in tomato, onion, lime and cilantro
Salsa | 10 | tomato, onion, cilantro, lime, chili, salt | Chop everything; Mix and rest
Tomato Soup | 30 | tomato, onion, garlic, butter, cream, water | Soften onion and garlic; Simmer with tomato; Blend and stir in cream
Tomato Rice | 25 | rice, tomato, onion, garlic, oil, cumin | Fry onion and garlic; Add tomato and rice; Cook with water
Bruschetta | 15 | bread, tomato, garlic, basil, olive oil | Toast bread; Top with tomato, garlic and basil
Margherita Pizza | 30 | flour, tomato, mozzarella, basil, olive oil, yeast | Make and rest the dough; Top with tomato and mozzarella; Bake hot
Cheese Pizza Toast | 15 | bread, tomato sauce, cheese, oregano | Spread sauce on bread; Top with cheese and oregano; Bake
Vegetable Soup | 35 | carrot, potato, onion, celery, tomato, garlic, water | Chop vegetables; Simmer in water until tender
Carrot Soup | 35 | carrot, onion, garlic, butter, ginger, water | Soften onion and garlic; Simmer with carrot and ginger; Blend
Pumpkin Soup | 40 | pumpkin, onion, garlic, cream, butter, water | Roast pumpkin; Simmer with onion and garlic; Blend with cream
Mushroom Soup | 30 | mushroom, onion, garlic, cream, butter, water | Brown mushrooms; Simmer with onion and garlic; Blend with cream
Broccoli Cheese Soup | 30 | broccoli, cheese, onion, milk, butter, flour | Soften onion; Simmer broccoli in milk; Stir in cheese
Cauliflower Cheese | 40 | cauliflower, cheese, milk, butter, flour | Boil cauliflower; Make cheese sauce; Bake until bubbly
Roasted Vegetables | 40 | carrot, potato, onion, bell pepper, olive oil, thyme | Chop vegetables; Toss with oil and thyme; Roast
Stir Fried Vegetables | 15 | broccoli, carrot, bell pepper, garlic, soy sauce, oil | Stir fry vegetables; Finish with soy sauce
Garlic Mushrooms | 15 | mushroom, garlic, butter, parsley, lemon | Fry mushrooms in butter; Add garlic and parsley; Finish with lemon
Sauteed Spinach | 10 | spinach, garlic, olive oil, lemon, salt | Warm garlic in oil; Wilt spinach; Squeeze lemon
Creamed Spinach | 20 | spinach, cream, garlic, butter, cheese | Wilt spinach; Simmer with cream and garlic; Stir in cheese
Spinach Pasta | 20 | pasta, spinach, garlic, cheese, olive oil | Boil pasta; Wilt spinach with garlic; Toss with cheese
Zucchini Fritters | 25 | zucchini, eggs, flour, cheese, oil | Grate zucchini; Mix with egg, flour and cheese; Fry
Stuffed Bell Peppers | 50 | bell pepper, rice, beef, onion, tomato, cheese | Cook filling; Stuff peppers; Bake until tender
Eggplant Parmesan | 55 | eggplant, tomato sauce, mozzarella, parmesan, flour, eggs | Bread and fry eggplant; Layer with sauce and cheese; Bake
Baba Ganoush | 40 | eggplant, tahini, garlic, lemon, olive oil | Roast eggplant; Blend with tahini, garlic and lemon
Ratatouille | 55 | eggplant, zucchini, tomato, bell pepper, onion, garlic, olive oil | Slice vegetables; Stew in oil with garlic until soft
Corn Salad | 15 | corn, tomato, onion, lime, cilantro, olive oil | Mix corn, tomato and onion; Dress with lime and oil
Fried Fish | 20 | fish, flour, lemon, eggs, oil, salt | Coat fish in egg and flour; Fry until crisp; Serve with lemon
Lemon Butter Fish | 20 | fish, lemon, butter, garlic, parsley | Pan fry fish in butter; Add garlic and lemon
Garlic Shrimp | 15 | shrimp, garlic, butter, lemon, parsley | Saute garlic in butter; Cook shrimp; Finish with lemon
Shrimp Fried Rice | 20 | shrimp, rice, eggs, pea, soy sauce, garlic, oil | Scramble eggs; Fry shrimp, garlic and rice; Season with soy sauce
Shrimp Pasta | 25 | shrimp, pasta, garlic, tomato, olive oil, parsley | Boil pasta; Saute garlic and shrimp; Toss with tomato and parsley
Sausage Pasta | 25 | sausage, pasta, tomato, onion, garlic, cheese | Brown sausage; Add onion and tomato; Toss with pasta
Sausage and Potatoes | 40 | sausage, potato, onion, olive oil, thyme | Chop everything; Roast with oil and thyme
Bacon and Eggs | 12 | bacon, eggs, bread, butter | Fry bacon; Fry eggs; Serve with toast
BLT Sandwich | 12 | bacon, lettuce, tomato, bread, mayonnaise | Crisp the bacon; Layer with lettuce and tomato in bread
Ham and Cheese Sandwich | 8 | ham, cheese, bread, butter, mustard | Layer ham and cheese on buttered bread
Ham Fried Rice | 15 | ham, rice, eggs, pea, soy sauce, oil | Fry ham and peas; Add rice and eggs; Season
Turkey Wrap | 10 | turkey, tortilla, lettuce, tomato, mayonnaise | Fill tortilla with turkey and vegetables; Roll
Pork Fried Noodles | 20 | pork, noodles, cabbage, carrot, soy sauce, garlic, oil | Stir fry pork; Add noodles and vegetables; Season
Vegetable Noodles | 15 | noodles, carrot, cabbage, garlic, soy sauce, oil | Boil noodles; Stir fry vegetables; Toss together
Tofu Stir Fry | 20 | tofu, broccoli, carrot, garlic, soy sauce, ginger, oil | Crisp tofu; Add vegetables, garlic and ginger; Finish with soy sauce
Scrambled Tofu | 15 | tofu, onion, tomato, cumin, oil, salt | Fry onion; Crumble in tofu and tomato; Season with cumin
Coconut Curry | 35 | coconut milk, potato, onion, garlic, ginger, chili powder, oil | Fry aromatics; Add potato and coconut milk; Simmer
Coconut Rice | 25 | rice, coconut milk, salt, water, sugar | Simmer rice in coconut milk and water
Peanut Butter Toast | 5 | bread, peanut butter, banana, honey | Toast bread; Spread peanut butter; Top with banana and honey
Honey Lemon Tea | 5 | lemon, honey, ginger, water | Steep ginger in hot water; Add lemon and honey
Lemonade | 10 | lemon, sugar, water | Juice lemons; Mix with sugar and cold water
Garlic Bread | 15 | bread, garlic, butter, parsley | Mix garlic and parsley into butter; Spread on bread; Bake
Onion Soup | 50 | onion, butter, bread, cheese, water, thyme | Slowly brown onions; Add water and thyme; Top with bread and cheese and grill
Mac and Cheese | 30 | pasta, cheese, milk, butter, flour | Boil pasta; Make cheese sauce with butter, flour and milk; Combine
Cheese Omelette | 8 | eggs, cheese, butter, salt | Beat eggs; Cook in butter; Add cheese and fold
Cabbage Stir Fry | 15 | cabbage, carrot, garlic, soy sauce, oil, ginger | Stir fry cabbage and carrot; Add garlic, ginger and soy sauce
Cabbage Soup | 35 | cabbage, carrot, onion, tomato, garlic, water | Soften vegetables; Simmer in water with tomato
Kale and Potato Soup | 35 | kale, potato, onion, garlic, olive oil, water | Soften onion and garlic; Simmer with potato; Add kale
Sweet Potato Fries | 35 | sweet potato, olive oil, paprika, salt | Cut into sticks; Toss with oil and paprika; Roast
Mashed Sweet Potato | 30 | sweet potato, butter, milk, cinnamon | Boil sweet potatoes; Mash with butter and milk
Green Bean Saute | 15 | green bean, garlic, butter, lemon, salt | Blanch beans; Saute with garlic and butter; Add lemon
Peas Pulao | 30 | rice, pea, onion, cumin, ginger, oil, water | Fry onion and cumin; Add rice, peas and water; Cook until fluffy
Celery Tuna Boats | 10 | celery, tuna, mayonnaise, lemon | Mix tuna with mayonnaise and lemon; Fill celery sticks
Pear and Cheese Plate | 5 | pear, cheese, honey, bread | Slice pear; Serve with cheese, bread and honey
Orange Chicken | 35 | chicken, orange, soy sauce, garlic, ginger, oil | Brown chicken; Simmer with orange juice, soy sauce, garlic and ginger
Mango Lassi | 5 | mango, yogurt, milk, sugar | Blend until smooth
Shallot Pasta | 20 | pasta, shallot, butter, parsley, cream | Soften shallot in butter; Add cream; Toss with pasta and parsley
Pesto Pasta | 15 | pasta, basil, garlic, parmesan, olive oil | Blend basil, garlic, parmesan and oil; Toss with hot pasta
Green Onion Egg Pancake | 15 | eggs, green onion, flour, oil, salt, water | Mix batter; Fry thin pancakes with green onion
""".strip()

out = []
for line in RAW.splitlines():
    name, mins, ings, steps = [p.strip() for p in line.split("|")]
    out.append({"name": name, "minutes": int(mins),
                "ingredients": [i.strip() for i in ings.split(",")],
                "steps": [s.strip() + "." for s in steps.split(";")]})

if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "data", "sample_recipes.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print("wrote", len(out), "recipes")
