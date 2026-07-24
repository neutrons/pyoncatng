# Widgets

Reusable NiceGUI widgets provided by `pyoncatng`. Each widget can be dropped into
any NiceGUI page; see the [Tutorials](tutorials.md) for runnable examples.

## Login

```{figure} media/login-widget-overview.png
:alt: ONCat login widget in row and column orientations, disconnected and connected states, plus sign-in dialog
:width: 100%

The login widget supports arranging the "connect" and "log out" buttons as
`orientation="row"` or `orientation="column"`.
The status indicator shows disconnected (empty circle) and connected states (green circle),
and the sign-in dialog provides the browser approval link and device code.
```

```{eval-rst}
.. autoclass:: pyoncatng.widgets.login.OncatLogin
   :members:
```
