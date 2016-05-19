# d3-guardian
Visualisations based on data from the Guardian's Open Platform API.

---

## MP relations
__Shows the relationship between MPs in the media.__  The script gets all current MPs from House of Commons API and cross-matches each MP using the Guardian's Open Platform to see if two MPs are mentioned it the same article. The result is a [hierarchical edge layout](https://bl.ocks.org/mbostock/7607999) showing relationships between MPs, clustered by party. [Hovering](https://wietze.github.io/d3-guardian/mp-relations/mps2.png) over the names of the MPs will highlight the relationships of the MP in question.

 __[:: Live demo](https://wietze.github.io/d3-guardian/mp-relations/d3.html)__

![Example of this d3 template.](https://wietze.github.io/d3-guardian/mp-relations/mps1.png)
